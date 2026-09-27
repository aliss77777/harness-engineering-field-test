"""Experiment 3 learning: decision-trace feedback for the Jev loop.

Two arms, run in parallel, both starting from experiment 2's version 0 rubric:
  Bp (B-prime): trace feedback + practice pre-screen; unweighted sum (as in B).
  Bw (B-plus):  the same, but each version's question weights are fitted on practice.

Loop A is not rerun: its experiment-2 final version is the comparison. Gate rule,
edit limits, question check and duplicate refusal are exactly experiment 2's.
Sealed data is never read here.
"""
from __future__ import annotations

import argparse
import json
import threading
import traceback
from typing import Any

from candidates import (
    InvalidCandidate, apply_candidate, candidate_prompt, candidate_schema, changed_question,
    describe, is_near_duplicate, signature, validate_version,
)
from evaluation import evaluate_loop_b, summarize
from evidence import build_evidence_table
from gate import best_passing, gate_version
from learn import LoopRunner
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from openrouter_llm import ContentBlockedError
from spend import SpendTracker
from telemetry import Telemetry
from trace import aggregate_trace, fit_weights, mistake_trace, rescore, rich_evidence
from workspace import Workspace


ARMS = {"Bp": "B-prime (decision trace)", "Bw": "B-plus (decision trace + fitted weights)"}

TRACE_GUIDANCE = """

HOW TO READ THE DECISION TRACE. The rubric's pick is a sum over questions, so each pick splits exactly
into per-question pushes. For every mistake, `trace` lists the questions that pushed hardest and toward
which response; `pushed_toward_winner: false` means that question helped cause the mistake.
`aggregate_trace` totals this over all practice pairs: `mistakes_pushed_toward_loser` (the question keeps
causing errors), `decisive_and_wrong` vs `decisive_and_right` (pairs where that question alone flipped the
pick). `rich_evidence.win_rate_by_gap` shows whether a bigger probability gap on a question means a more
reliable pick, and `overlapping_questions` lists questions that measure nearly the same thing.
Use this to target the criterion that is actually wrong: flip or reword a question that is decisive-and-wrong,
drop one that is redundant or noise, and add a question only for a pattern the current questions miss."""


class TraceRunner(LoopRunner):
    def __init__(self, ws: Workspace, arm: str, **kwargs: Any):
        super().__init__(ws, "B", **kwargs)
        self.arm = arm
        self.weighted = arm == "Bw"

    # Every record, log line and telemetry lane is labelled with the arm, not "B".
    def evaluate(self, version: dict[str, Any], version_id: str, set_name: str, round_number: int) -> list[dict[str, Any]]:
        if self.stop.is_set():
            raise RuntimeError("stopped because the other arm failed")
        frame = self.practice if set_name == "practice" else self.gate_frame

        def progress(**values):
            self.telemetry.stage(self.arm, stage="evaluate", round=round_number, set=set_name,
                                 version_id=version_id, **values)

        records = evaluate_loop_b(self.ws, frame, version["rubric_questions"], client=self.jev, logger=self.logger,
                                  run_id=self.run_id, round_number=round_number, set_name=set_name,
                                  version_id=version_id, progress=progress, weights=version.get("weights"),
                                  loop=self.arm)
        self.telemetry.evaluation(loop=self.arm, round_number=round_number, set_name=set_name,
                                  version_id=version_id, summary=summarize(records))
        return records

    def with_weights(self, version: dict[str, Any], version_id: str, round_number: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Score a version on practice. For Bw, fit its weights there first (no extra API calls)."""
        version = {k: v for k, v in version.items() if k != "weights"}
        raw = self.evaluate(version, version_id, "practice", round_number)
        if not self.weighted:
            return version, raw
        weights = fit_weights(raw, version["rubric_questions"], c=self.config["learning"]["weights"]["regularization_c"],
                              seed=self.config["seed"])
        records = rescore(raw, version["rubric_questions"], weights, seed=self.config["seed"], label=f"{version_id}:practice")
        self.logger.write({"run_id": self.run_id, "loop": self.arm, "round": round_number, "set": "practice",
                           "call_type": "weights_fit", "version_id": version_id, "weights": weights,
                           "in_sample_accuracy": summarize(records)["accuracy"]})
        return {**version, "weights": weights}, records

    def feedback(self, records: list[dict[str, Any]], version: dict[str, Any], round_number: int,
                 attempt: int = 1) -> dict[str, Any]:
        base = super().feedback(records, version, round_number, attempt)
        questions, weights = version["rubric_questions"], version.get("weights")
        by_id = {r["pair_id"]: r for r in records}
        for entry in base["mistakes"]:
            entry["trace"] = mistake_trace(by_id[entry["pair_id"]], questions, self.ws.labels, weights)
        trace_config = self.config["learning"]["trace"]
        base["evidence_table"] = build_evidence_table(records, [q["question_id"] for q in questions])
        base["aggregate_trace"] = aggregate_trace(records, questions, weights)
        base["rich_evidence"] = rich_evidence(records, questions, trace_config["gap_bins"], trace_config["overlap_threshold"])
        if weights is not None:
            base["fitted_weights"] = {**weights, "_note": "fitted on practice; negative = direction looks backwards"}
        return base

    def propose(self, current: dict[str, Any], feedback: dict[str, Any], round_number: int, version_id: str) -> list[dict[str, Any]]:
        proposals = self.config["learning"]["prescreen"]["proposals"]
        owned = {k: v for k, v in current.items() if k != "weights"}
        prompt = candidate_prompt(loop="B", current=owned, feedback=feedback, history=self.history,
                                  rejected=self.rejected, config=self.config, wording=self.ws.wording,
                                  max_items=proposals, guidance=TRACE_GUIDANCE)
        event = {"run_id": self.run_id, "loop": "editor", "round": round_number, "set": "practice",
                 "pair_id": None, "version_id": version_id, "call_type": "candidate_proposal", "target_loop": self.arm}
        try:
            return self.llm.generate_json(prompt=prompt, schema=candidate_schema("B", self.config, proposals),
                                          event=event)["candidates"]
        except ContentBlockedError:
            raise
        except Exception as error:
            # Stop rather than record a silent "no edits" round; finished calls are cached.
            self.logger.write({**event, "call_type": "candidate_proposal_failed", "error": str(error)})
            raise

    def run(self, version0: dict[str, Any]) -> dict[str, Any]:
        learning = self.config["learning"]
        prescreen = learning["prescreen"]
        current, practice_current = self.with_weights({"version_id": f"{self.arm}-v0", **version0}, f"{self.arm}-v0", 1)
        current["version_id"] = f"{self.arm}-v0"
        self.version0 = dict(current)  # Bw: the v0 rubric with its fitted weights
        self.telemetry.current(self.arm, current)
        gate_current = self.evaluate(current, current["version_id"], "gate", 1)
        for round_number in range(1, learning["rounds"] + 1):
            owned = {k: v for k, v in current.items() if k not in ("version_id", "weights")}
            proposals: list[dict[str, Any]] = []
            for attempt in (1, 2, 3):
                feedback = self.feedback(practice_current, current, round_number, attempt)
                try:
                    proposals = self.propose(owned, feedback, round_number, current["version_id"])
                    break
                except ContentBlockedError:
                    self.telemetry.note(f"{self.arm} round {round_number}: editor prompt blocked (attempt {attempt})")

            screened: list[tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = []
            round_signatures: list[str] = []
            for index, proposal in enumerate(proposals[: prescreen["proposals"]], start=1):
                self.candidate_count += 1
                candidate_id = f"{self.arm}-r{round_number}-c{index}"
                record: dict[str, Any] = {
                    "run_id": self.run_id, "loop": self.arm, "round": round_number, "candidate_id": candidate_id,
                    "based_on": current["version_id"], "operation": proposal.get("operation"), "change": None,
                    "reason": " ".join(str(proposal.get("reason", "")).split())}
                try:
                    record["change"] = describe("B", proposal)
                    sig = signature("B", proposal)
                    if is_near_duplicate(sig, self.rejected + round_signatures, learning["duplicate_similarity"]):
                        record["status"] = "refused_duplicate_of_rejected"
                    else:
                        round_signatures.append(sig)
                        record["sig"] = sig
                        new_version = apply_candidate("B", owned, proposal, self.config)
                        validate_version("B", new_version, self.config)
                        question = changed_question("B", proposal, new_version)
                        if question is not None and not self.question_check(question, round_number, candidate_id):
                            record["status"] = "failed_question_check"
                            self.rejected.append(sig)
                        else:
                            version, practice_records = self.with_weights(new_version, candidate_id, round_number)
                            version["version_id"] = candidate_id
                            outcome = gate_version([r["correct"] for r in practice_current],
                                                   [r["correct"] for r in practice_records], p_threshold=1.0)
                            record.update(practice_b=outcome.b, practice_c=outcome.c,
                                          practice_accuracy=round(summarize(practice_records)["accuracy"], 4),
                                          current_practice_accuracy=round(summarize(practice_current)["accuracy"], 4))
                            record["status"] = "prescreened"
                            screened.append((candidate_id, version, practice_records, record))
                except (InvalidCandidate, ValueError, KeyError) as error:
                    record["status"] = "invalid"
                    record["error"] = str(error)
                if record["status"] != "prescreened":
                    self._close(record)

            # Gate only the best few with a net gain on practice.
            ranked = sorted((item for item in screened if item[3]["practice_b"] > item[3]["practice_c"]),
                            key=lambda item: (-(item[3]["practice_b"] - item[3]["practice_c"]), item[0]))
            to_gate = ranked[: prescreen["gate_top"]]
            for candidate_id, _, _, record in screened:
                if all(candidate_id != item[0] for item in to_gate):
                    record["status"] = "not_selected_by_prescreen"
                    self.rejected.append(record["sig"])
                    self._close(record)

            gated, versions = [], {}
            for candidate_id, version, practice_records, record in to_gate:
                gate_records = self.evaluate(version, candidate_id, "gate", round_number)
                outcome = gate_version([r["correct"] for r in gate_current], [r["correct"] for r in gate_records],
                                       p_threshold=learning["gate_p_threshold"])
                gated.append((candidate_id, outcome))
                versions[candidate_id] = (version, practice_records, gate_records, record)
                record.update(b=outcome.b, c=outcome.c, p=round(outcome.p_value, 6), passed=outcome.keep,
                              gate_accuracy=round(summarize(gate_records)["accuracy"], 4),
                              current_gate_accuracy=round(summarize(gate_current)["accuracy"], 4))
            winner = best_passing(gated)
            for candidate_id, _ in gated:
                record = versions[candidate_id][3]
                record["kept"] = candidate_id == winner
                record["status"] = "kept" if record["kept"] else ("passed_not_best" if record["passed"] else "rejected")
                if not record["kept"]:
                    self.rejected.append(record["sig"])
                self._close(record, call_type="gate")
            self.telemetry.gate({"loop": self.arm, "round": round_number, "kept": winner, "proposed": len(proposals),
                                 "prescreened": len(screened), "gated": len(gated),
                                 "results": {cid: {"b": o.b, "c": o.c, "p": round(o.p_value, 6), "passed": o.keep}
                                             for cid, o in gated}})
            if winner is not None:
                current, practice_current, gate_current = versions[winner][0], versions[winner][1], versions[winner][2]
                self.kept_count += 1
                self.telemetry.current(self.arm, current)
        self.telemetry.finish(self.arm, round=learning["rounds"], kept=self.kept_count)
        return current

    def _close(self, record: dict[str, Any], call_type: str = "candidate") -> None:
        clean = {k: v for k, v in record.items() if k != "sig"}
        self.history.append({k: v for k, v in clean.items() if k != "run_id"})
        self.logger.write({**clean, "call_type": call_type, **({"set": "gate"} if call_type == "gate" else {})})
        self.telemetry.candidate(clean)


def run_learning(ws: Workspace, run_id: str) -> dict[str, Any]:
    config = ws.config
    results = ws.path("results")
    frozen_path = results / "final_versions.json"
    if frozen_path.exists():
        raise RuntimeError("final versions are already frozen; refusing to rerun learning")
    version0 = json.loads((ws.root / config["experiment2"]["results"] / "version0.json").read_text())
    spend = SpendTracker(results / "spend.json", config["budget"]["spend_cap_usd"])
    logs = ws.path("logs")
    logger = JsonlLogger(logs / f"{run_id}.jsonl")
    telemetry = Telemetry(results, run_id, spend)
    llm = build_llm_client(config, ws.root, run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(config, ws.root, run_id, logs_dir=logs, spend=spend)
    stop = threading.Event()
    runners = {arm: TraceRunner(ws, arm, run_id=run_id, llm=llm, jev=jev, logger=logger, telemetry=telemetry, stop=stop)
               for arm in ARMS}
    start = {"rubric_questions": version0["rubric_questions"]}
    finals: dict[str, Any] = {}
    errors: dict[str, str] = {}

    def work(arm: str) -> None:
        try:
            finals[arm] = runners[arm].run(start)
        except Exception as error:
            errors[arm] = f"{type(error).__name__}: {error}"
            stop.set()
            telemetry.stage(arm, stage="failed", error=errors[arm])
            traceback.print_exc()

    threads = [threading.Thread(target=work, args=(arm,), name=f"arm-{arm}") for arm in ARMS]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    spend.flush()
    if errors:
        raise RuntimeError(f"learning failed: {errors}")
    frozen = {
        "frozen": True, "run_id": run_id, "rounds": config["learning"]["rounds"], "arms": ARMS,
        "version0": {"rubric_questions": version0["rubric_questions"]},
        "arm_version0": {arm: runner.version0 for arm, runner in runners.items()}, "final": finals,
        "history": {arm: runner.history for arm, runner in runners.items()},
        "edits": {arm: {"proposed": runner.candidate_count, "kept": runner.kept_count} for arm, runner in runners.items()},
        "notes": {"task": ws.task["name"], "feedback_mode": config["learning"]["feedback_mode"],
                  "prescreen": config["learning"]["prescreen"], "gate_p_threshold": config["learning"]["gate_p_threshold"],
                  "learning_paid_spend_usd": round(spend.total_usd, 4)},
    }
    frozen_path.write_text(json.dumps(frozen, indent=2) + "\n")
    telemetry.note("learning complete; final versions frozen")
    return frozen


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 3 learning (Jev arms only; no sealed data).")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_arena3.yaml")
    parser.add_argument("--task", default="task_arena3.yaml")
    args = parser.parse_args()
    result = run_learning(Workspace.load(args.config, args.task), args.run_id)
    print(json.dumps(result["edits"]))


if __name__ == "__main__":
    main()
