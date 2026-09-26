from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from deciders import RubricQuestion
from editor import make_rewordings, propose_edit, validate_edit
from evaluation import evaluate_loop_a, evaluate_loop_b, summarize
from evidence import build_evidence_table
from gate import gate_version
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from progress import RunProgress


ROOT = Path(__file__).resolve().parent


def feedback_for(loop: str, records: list[dict[str, Any]], current: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    mistakes = [item for item in records if not item["correct"]][: config["learning"]["feedback_mistakes"]]
    compact = [{key: item.get(key) for key in (
        "pair_id", "headline_x", "headline_y", "prediction", "winner", "reason"
    )} for item in mistakes]
    result: dict[str, Any] = {"accuracy": summarize(records)["accuracy"], "mistakes": compact}
    if loop == "B":
        ids = [item["question_id"] for item in current["rubric_questions"]]
        result["evidence_table"] = build_evidence_table(records, ids)
    return result


def check_changed_questions(proposal: dict[str, Any], current: dict[str, Any], *, practice, llm, jev, logger, config, run_id, round_number) -> dict[str, Any]:
    old = {item["question_id"]: item for item in current["rubric_questions"]}
    changed = [item for item in proposal["rubric_questions"] if item["question_id"] not in old or item["text"] != old[item["question_id"]]["text"]]
    headlines = [headline for _, row in practice.head(5).iterrows() for headline in (row["headline_x"], row["headline_y"])]
    rejected: set[str] = set()
    for question in changed:
        passed = False
        disagreements = None
        for attempt in (1, 2):
            texts = make_rewordings(
                question=question, client=llm,
                event={"run_id": run_id, "loop": "editor", "round": round_number, "set": "practice",
                       "pair_id": None, "version_id": f"B-r{round_number}-proposed",
                       "call_type": "question_rewording", "question_id": question["question_id"], "attempt": attempt},
            )
            variants = [RubricQuestion(question["question_id"], text, question["direction"]) for text in texts]
            disagreements = 0
            for index, headline in enumerate(headlines):
                answers = [jev.evaluate(
                    headline, [variant],
                    {"run_id": run_id, "loop": "B", "round": round_number, "set": "practice",
                     "pair_id": f"question-check-{index}", "version_id": f"B-r{round_number}-proposed",
                     "call_type": "question_check", "question_id": question["question_id"], "wording": wording},
                    use_cache=False,
                )[question["question_id"]] for wording, variant in enumerate(variants, start=1)]
                disagreements += int((answers[0] >= 0.5) != (answers[1] >= 0.5))
            logger.write({"run_id": run_id, "loop": "B", "round": round_number, "set": "practice",
                          "call_type": "question_check_result", "question_id": question["question_id"],
                          "attempt": attempt, "disagreements": disagreements, "passed": disagreements <= 1})
            if disagreements <= 1:
                passed = True
                break
        if not passed:
            rejected.add(question["question_id"])

    if rejected:
        retained = []
        for question in proposal["rubric_questions"]:
            if question["question_id"] not in rejected:
                retained.append(question)
            elif question["question_id"] in old:
                retained.append(old[question["question_id"]])
        proposal = {**proposal, "rubric_questions": retained}
        validate_edit(proposal, "B", config)
    return proposal


def run_learning(run_id: str) -> dict[str, Any]:
    frozen_path = ROOT / "results" / "final_versions.json"
    if frozen_path.exists():
        raise RuntimeError("final versions are already frozen; refusing to rerun learning")
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    version0 = json.loads((ROOT / "results" / "version0.json").read_text())
    practice = pd.read_csv(ROOT / "data" / "pairs" / "practice.csv", dtype={"pair_id": str})
    gate_frame = pd.read_csv(ROOT / "data" / "pairs" / "gate.csv", dtype={"pair_id": str})
    logger = JsonlLogger(ROOT / "logs" / f"{run_id}.jsonl")
    status = RunProgress(ROOT / "results" / "run_status.json", run_id)
    llm = build_llm_client(config, ROOT, run_id)
    jev = build_jev_client(config, ROOT, run_id)
    current = {
        "A": {"version_id": "A-v0", "instructions": version0["instructions"]},
        "B": {"version_id": "B-v0", "rubric_questions": version0["rubric_questions"]},
    }
    histories: dict[str, list[dict[str, Any]]] = {"A": [], "B": []}
    gate_current: dict[str, list[dict[str, Any]] | None] = {"A": None, "B": None}

    for round_number in range(1, config["learning"]["rounds"] + 1):
        for loop in ("A", "B"):
            def stage_progress(**values):
                status.update(stage="learning", loop=loop, round=round_number, set="practice", **values)
            if loop == "A":
                practice_records = evaluate_loop_a(practice, current[loop]["instructions"], client=llm, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="practice", version_id=current[loop]["version_id"], progress=stage_progress)
            else:
                practice_records = evaluate_loop_b(practice, current[loop]["rubric_questions"], client=jev, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="practice", version_id=current[loop]["version_id"], progress=stage_progress)
            feedback = feedback_for(loop, practice_records, current[loop], config)
            proposal = propose_edit(
                loop=loop, current=current[loop], feedback=feedback, history=histories[loop], client=llm, config=config,
                event={"run_id": run_id, "loop": "editor", "round": round_number, "set": "practice",
                       "pair_id": None, "version_id": current[loop]["version_id"], "call_type": "edit_proposal", "target_loop": loop},
            )
            proposal["version_id"] = f"{loop}-r{round_number}-proposed"
            if loop == "B":
                proposal = check_changed_questions(proposal, current[loop], practice=practice, llm=llm, jev=jev, logger=logger, config=config, run_id=run_id, round_number=round_number)
            logger.write({"run_id": run_id, "loop": "editor", "round": round_number, "set": "practice",
                          "call_type": "edit_proposal_result", "target_loop": loop,
                          "version_id": proposal["version_id"], "changes": proposal["changes"]})

            def gate_progress(**values):
                status.update(stage="learning", loop=loop, round=round_number, set="gate", **values)

            if gate_current[loop] is None:
                gate_current[loop] = (
                    evaluate_loop_a(gate_frame, current[loop]["instructions"], client=llm, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="gate", version_id=current[loop]["version_id"], progress=gate_progress)
                    if loop == "A" else
                    evaluate_loop_b(gate_frame, current[loop]["rubric_questions"], client=jev, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="gate", version_id=current[loop]["version_id"], progress=gate_progress)
                )
            proposed_gate = (
                evaluate_loop_a(gate_frame, proposal["instructions"], client=llm, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="gate", version_id=proposal["version_id"], progress=gate_progress)
                if loop == "A" else
                evaluate_loop_b(gate_frame, proposal["rubric_questions"], client=jev, logger=logger, config=config, run_id=run_id, round_number=round_number, set_name="gate", version_id=proposal["version_id"], progress=gate_progress)
            )
            outcome = gate_version(
                [item["correct"] for item in gate_current[loop]],
                [item["correct"] for item in proposed_gate],
                p_threshold=config["learning"]["gate_p_threshold"],
            )
            gate_record = {"run_id": run_id, "loop": loop, "round": round_number, "set": "gate",
                           "call_type": "gate", "version_id": proposal["version_id"],
                           "keep": outcome.keep, "b": outcome.b, "c": outcome.c, "p": outcome.p_value,
                           "changes": proposal["changes"]}
            logger.write(gate_record)
            histories[loop].append(gate_record)
            if outcome.keep:
                current[loop] = proposal
                gate_current[loop] = proposed_gate

    frozen = {
        "frozen": True, "run_id": run_id, "rounds": config["learning"]["rounds"],
        "version0": version0, "final": current, "history": histories,
        "notes": {
            "loop_a_batch_size": config["api"]["batch_size"],
            "loop_a_reasoning_effort": config["api"]["reasoning_effort"],
            "version0_route": "Gemini 3.8 Flash via Google directly",
            "later_route": "OpenRouter",
            "question_check_mode": config["learning"]["question_check_mode"],
        },
    }
    frozen_path.write_text(json.dumps(frozen, indent=2) + "\n")
    status.update(stage="learning_complete", loop=None, round=config["learning"]["rounds"], set=None, completed=1, total=1)
    return frozen


def main() -> None:
    parser = argparse.ArgumentParser(description="Run four learning rounds without touching sealed data.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = run_learning(args.run_id)
    print(f"Frozen final versions after {result['rounds']} rounds per loop. Sealed set was not run.")


if __name__ == "__main__":
    main()
