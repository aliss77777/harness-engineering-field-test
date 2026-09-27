"""Learning rounds for Loops A and B (single-edit gating, Task Brief 2 section 2).

Experiment 1 used bundle gating; its exact code is at git tag exp1-upworthy-v1.
Sealed data is never read here.
"""
from __future__ import annotations

import argparse
import json
import threading
import traceback
from typing import Any

import pandas as pd

from candidates import (
    InvalidCandidate, apply_candidate, candidate_prompt, candidate_schema, changed_question,
    describe, is_near_duplicate, sample_mistakes, signature, trim, validate_version,
)
from deciders import RubricQuestion
from editor import make_rewordings
from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from evidence import build_evidence_table
from gate import best_passing, gate_version
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from openrouter_llm import ContentBlockedError
from spend import SpendTracker
from telemetry import Telemetry
from workspace import Workspace


class LoopRunner:
    def __init__(self, ws: Workspace, loop: str, *, run_id: str, llm, jev, logger, telemetry: Telemetry,
                 stop: threading.Event | None = None):
        self.ws, self.loop, self.run_id = ws, loop, run_id
        self.stop = stop or threading.Event()
        self.config = ws.config
        self.llm, self.jev, self.logger, self.telemetry = llm, jev, logger, telemetry
        pairs_dir = ws.path("pairs")
        self.practice = pd.read_csv(pairs_dir / "practice.csv", dtype={"pair_id": str})
        self.gate_frame = pd.read_csv(pairs_dir / "gate.csv", dtype={"pair_id": str})
        self.practice_by_id = self.practice.set_index("pair_id")
        self.history: list[dict[str, Any]] = []
        self.rejected: list[str] = []
        self.kept_count = 0
        self.candidate_count = 0

    # --- evaluation -------------------------------------------------------
    def evaluate(self, version: dict[str, Any], version_id: str, set_name: str, round_number: int) -> list[dict[str, Any]]:
        if self.stop.is_set():
            raise RuntimeError("stopped because the other loop failed")
        frame = self.practice if set_name == "practice" else self.gate_frame

        def progress(**values):
            self.telemetry.stage(self.loop, stage="evaluate", round=round_number, set=set_name,
                                 version_id=version_id, **values)

        common = dict(client=self.llm if self.loop == "A" else self.jev, logger=self.logger,
                      run_id=self.run_id, round_number=round_number, set_name=set_name,
                      version_id=version_id, progress=progress)
        records = (evaluate_loop_a(self.ws, frame, version["instructions"], **common) if self.loop == "A"
                   else evaluate_loop_b(self.ws, frame, version["rubric_questions"], **common))
        self.telemetry.evaluation(loop=self.loop, round_number=round_number, set_name=set_name,
                                  version_id=version_id, summary=summarize(records))
        return records

    # --- editor feedback ----------------------------------------------------
    def feedback(self, records: list[dict[str, Any]], version: dict[str, Any], round_number: int,
                 attempt: int = 1) -> dict[str, Any]:
        learning = self.config["learning"]
        labels, limit = self.ws.labels, learning["editor_item_word_limit"]
        columns = self.ws.columns
        shown = {"X": labels["x"], "Y": labels["y"]}
        mistakes = []
        readable = [item for item in records if not item.get("blocked")]
        sample_round = round_number if attempt == 1 else f"{round_number}-retry{attempt}"
        for item in sample_mistakes(readable, count=learning["feedback_mistakes"], seed=self.config["seed"],
                                    round_number=sample_round, loop=self.loop):
            row = self.practice_by_id.loc[item["pair_id"]]
            entry = {"pair_id": item["pair_id"]}
            if columns["context"]:
                entry[self.ws.wording["context"]] = trim(row[columns["context"]], limit)
            entry[f"{self.ws.wording['item']}_{labels['x']}"] = trim(row[columns["x"]], limit)
            entry[f"{self.ws.wording['item']}_{labels['y']}"] = trim(row[columns["y"]], limit)
            entry["picked"] = shown[item["prediction"]]
            entry["actual_winner"] = shown[item["winner"]]
            if self.loop == "A":
                entry["decider_reason"] = item["reason"]
            mistakes.append(entry)
        result: dict[str, Any] = {"practice_accuracy": round(summarize(records)["accuracy"], 4), "mistakes": mistakes}
        if self.loop == "B":
            ids = [q["question_id"] for q in version["rubric_questions"]]
            table = build_evidence_table(records, ids)
            for row in table:
                row["yes_is_side"] = f"'{self.ws.labels['x']}'/'{self.ws.labels['y']}' per pair; yes = P(yes) >= 0.5"
            result["evidence_table"] = table
        return result

    # --- 5.4 question consistency check -------------------------------------------
    def question_check(self, question: dict[str, Any], round_number: int, candidate_id: str) -> bool:
        learning = self.config["learning"]
        n_pairs = max(1, learning["question_check_items"] // 2)
        states = [self.ws.jev_state(view["context"], view[side])
                  for view in (self.ws.pair_view(row) for _, row in self.practice.head(n_pairs).iterrows())
                  for side in ("x", "y")]
        for attempt in (1, 2):
            texts = make_rewordings(
                question=question, client=self.llm, item_scope=self.ws.wording.get("item_scope", "one item alone"),
                event={"run_id": self.run_id, "loop": "editor", "round": round_number, "set": "practice",
                       "pair_id": None, "version_id": candidate_id, "call_type": "question_rewording",
                       "question_id": question["question_id"], "attempt": attempt, "target_loop": "B"},
            )
            variants = [RubricQuestion(question["question_id"], text, question["direction"]) for text in texts]
            disagreements = 0
            for index, state in enumerate(states):
                answers = [self.jev.evaluate(
                    state, [variant],
                    {"run_id": self.run_id, "loop": "B", "round": round_number, "set": "practice",
                     "pair_id": f"question-check-{index}", "version_id": candidate_id,
                     "call_type": "question_check", "question_id": question["question_id"], "wording": wording},
                    use_cache=False,
                )[question["question_id"]] for wording, variant in enumerate(variants, start=1)]
                disagreements += int((answers[0] >= 0.5) != (answers[1] >= 0.5))
            passed = disagreements <= learning["question_check_max_disagreements"]
            self.logger.write({"run_id": self.run_id, "loop": "B", "round": round_number, "set": "practice",
                               "call_type": "question_check_result", "version_id": candidate_id,
                               "question_id": question["question_id"], "attempt": attempt,
                               "disagreements": disagreements, "passed": passed})
            if passed:
                return True
        return False

    # --- one round ----------------------------------------------------------------
    def propose(self, current: dict[str, Any], feedback: dict[str, Any], round_number: int, version_id: str) -> list[dict[str, Any]]:
        prompt = candidate_prompt(loop=self.loop, current=current, feedback=feedback, history=self.history,
                                  rejected=self.rejected, config=self.config, wording=self.ws.wording)
        event = {"run_id": self.run_id, "loop": "editor", "round": round_number, "set": "practice",
                 "pair_id": None, "version_id": version_id, "call_type": "candidate_proposal", "target_loop": self.loop}
        try:
            return self.llm.generate_json(prompt=prompt, schema=candidate_schema(self.loop, self.config), event=event)["candidates"]
        except ContentBlockedError:
            raise
        except Exception as error:
            # Never turn a failed editor call into "no edits this round": that would silently
            # waste a round. Log it and stop the loop; finished calls are cached for a rerun.
            self.logger.write({**event, "call_type": "candidate_proposal_failed", "error": str(error)})
            raise

    def run(self, version0: dict[str, Any]) -> dict[str, Any]:
        learning = self.config["learning"]
        current = {"version_id": f"{self.loop}-v0", **version0}
        self.telemetry.current(self.loop, current)
        gate_current: list[dict[str, Any]] | None = None
        for round_number in range(1, learning["rounds"] + 1):
            practice_records = self.evaluate(current, current["version_id"], "practice", round_number)
            if gate_current is None:
                gate_current = self.evaluate(current, current["version_id"], "gate", round_number)
            owned = {k: v for k, v in current.items() if k != "version_id"}
            proposals: list[dict[str, Any]] = []
            for attempt in (1, 2, 3):
                # If the provider refuses a mistake's text, show the editor a different sample.
                feedback = self.feedback(practice_records, current, round_number, attempt)
                try:
                    proposals = self.propose(owned, feedback, round_number, current["version_id"])
                    break
                except ContentBlockedError:
                    self.telemetry.note(f"Loop {self.loop} round {round_number}: editor prompt blocked "
                                        f"(attempt {attempt}); resampling mistakes")
            round_signatures: list[str] = []
            gated: list[tuple[str, Any]] = []
            versions: dict[str, tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = {}
            for index, proposal in enumerate(proposals[: learning["max_changes"]], start=1):
                self.candidate_count += 1
                candidate_id = f"{self.loop}-r{round_number}-c{index}"
                record = {"run_id": self.run_id, "loop": self.loop, "round": round_number,
                          "candidate_id": candidate_id, "based_on": current["version_id"],
                          "operation": proposal.get("operation"), "change": None,
                          "reason": " ".join(str(proposal.get("reason", "")).split())}
                try:
                    record["change"] = describe(self.loop, proposal)
                    sig = signature(self.loop, proposal)
                    if is_near_duplicate(sig, self.rejected + round_signatures, learning["duplicate_similarity"]):
                        record["status"] = "refused_duplicate_of_rejected"
                    else:
                        round_signatures.append(sig)
                        new_version = apply_candidate(self.loop, owned, proposal, self.config)
                        validate_version(self.loop, new_version, self.config)
                        question = changed_question(self.loop, proposal, new_version)
                        if question is not None and not self.question_check(question, round_number, candidate_id):
                            record["status"] = "failed_question_check"
                            self.rejected.append(sig)
                        else:
                            record["status"] = "gated"
                            versions[candidate_id] = ({"version_id": candidate_id, **new_version}, [], record)
                            record["sig"] = sig
                except (InvalidCandidate, ValueError, KeyError) as error:
                    record["status"] = "invalid"
                    record["error"] = str(error)
                if record["status"] != "gated":
                    self.history.append({k: v for k, v in record.items() if k not in ("run_id", "sig")})
                    self.logger.write({**record, "call_type": "candidate"})
                    self.telemetry.candidate(record)

            for candidate_id, (version, _, record) in versions.items():
                gate_records = self.evaluate(version, candidate_id, "gate", round_number)
                outcome = gate_version([r["correct"] for r in gate_current], [r["correct"] for r in gate_records],
                                       p_threshold=learning["gate_p_threshold"])
                gated.append((candidate_id, outcome))
                versions[candidate_id] = (version, gate_records, record)
                record.update(b=outcome.b, c=outcome.c, p=round(outcome.p_value, 6), passed=outcome.keep,
                              gate_accuracy=round(summarize(gate_records)["accuracy"], 4),
                              current_gate_accuracy=round(summarize(gate_current)["accuracy"], 4))

            winner = best_passing(gated)
            for candidate_id, _ in gated:
                version, gate_records, record = versions[candidate_id]
                record["kept"] = candidate_id == winner
                record["status"] = "kept" if record["kept"] else ("passed_not_best" if record["passed"] else "rejected")
                if not record["kept"]:
                    self.rejected.append(record["sig"])
                self.history.append({k: v for k, v in record.items() if k not in ("run_id", "sig")})
                self.logger.write({**{k: v for k, v in record.items() if k != "sig"}, "call_type": "gate", "set": "gate"})
                self.telemetry.candidate({k: v for k, v in record.items() if k != "sig"})
            self.telemetry.gate({"loop": self.loop, "round": round_number, "kept": winner,
                                 "proposed": len(proposals), "gated": len(gated),
                                 "results": {cid: {"b": o.b, "c": o.c, "p": round(o.p_value, 6), "passed": o.keep}
                                             for cid, o in gated}})
            if winner is not None:
                current, gate_current = versions[winner][0], versions[winner][1]
                self.kept_count += 1
                self.telemetry.current(self.loop, current)
        self.telemetry.finish(self.loop, round=learning["rounds"], kept=self.kept_count)
        return current


def run_learning(ws: Workspace, run_id: str) -> dict[str, Any]:
    config = ws.config
    if config["learning"].get("gate_mode") != "single_edit":
        raise RuntimeError("this runner implements single-edit gating; experiment 1 code is at tag exp1-upworthy-v1")
    results = ws.path("results")
    frozen_path = results / "final_versions.json"
    if frozen_path.exists():
        raise RuntimeError("final versions are already frozen; refusing to rerun learning")
    version0 = json.loads((results / "version0.json").read_text())
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{run_id}.jsonl")
    telemetry = Telemetry(results, run_id, spend)
    llm = build_llm_client(config, ws.root, run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, run_id, logs_dir=logs, spend=spend)
    starts = {"A": {"instructions": version0["instructions"]},
              "B": {"rubric_questions": version0["rubric_questions"]}}
    stop = threading.Event()
    runners = {loop: LoopRunner(ws, loop, run_id=run_id, llm=llm, jev=jev, logger=logger,
                                telemetry=telemetry, stop=stop)
               for loop in ("A", "B")}
    finals: dict[str, Any] = {}
    errors: dict[str, str] = {}

    def work(loop: str) -> None:
        try:
            finals[loop] = runners[loop].run(starts[loop])
        except Exception as error:
            errors[loop] = f"{type(error).__name__}: {error}"
            stop.set()  # the other loop stops at its next evaluation; its finished calls stay cached
            telemetry.stage(loop, stage="failed", error=errors[loop])
            traceback.print_exc()

    threads = [threading.Thread(target=work, args=(loop,), name=f"loop-{loop}") for loop in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    spend.flush()
    if errors:
        raise RuntimeError(f"learning failed: {errors}")

    frozen = {
        "frozen": True, "run_id": run_id, "rounds": config["learning"]["rounds"],
        "version0": version0, "final": finals,
        "history": {loop: runner.history for loop, runner in runners.items()},
        "edits": {loop: {"proposed": runner.candidate_count, "kept": runner.kept_count} for loop, runner in runners.items()},
        "notes": {
            "task": ws.task["name"],
            "gate_mode": config["learning"]["gate_mode"],
            "gate_p_threshold": config["learning"]["gate_p_threshold"],
            "loop_a_batch_size": config["api"]["batch_size"],
            "loop_a_reasoning_effort": config["api"]["reasoning_effort"],
            "question_check_mode": config["learning"]["question_check_mode"],
            "learning_paid_spend_usd": round(spend.total_usd, 4),
        },
    }
    frozen_path.write_text(json.dumps(frozen, indent=2) + "\n")
    telemetry.note("learning complete; final versions frozen")
    return frozen


def main() -> None:
    parser = argparse.ArgumentParser(description="Run learning rounds without touching sealed data.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena.yaml")
    parser.add_argument("--task", default="task_arena.yaml")
    args = parser.parse_args()
    result = run_learning(Workspace.load(args.config, args.task), args.run_id)
    print(f"Frozen final versions after {result['rounds']} rounds per loop. Sealed set was not run.")
    print(json.dumps(result["edits"]))


if __name__ == "__main__":
    main()
