"""Experiment 6: policies learning from partial feedback (contextual bandit on Upworthy).

Arms (all start from experiment 1's version 0):
  R  Jev + LLM router (primary): Jev scores every headline; if its top-vs-second margin is
     at least tau (the label-free quantile sending 40% of tests to the LLM), Jev picks;
     otherwise the LLM (fixed version-0 instructions) picks. The Jev rubric learns.
  L  LLM only: the LLM picks every test; its instructions learn.
  J  Jev only: the top-scoring headline; the rubric learns.
  C  Thompson sampling on six surface features (no LLM, no editor).

Each round: act on a new batch of 300 practice tests (15% seeded exploration), observe only
the chosen headline's click rate, let the editor propose single edits, and gate them by the
click rates of each policy's own greedy picks on the gate set.

    python learn_bandit.py --stage learn --run-id RUN_ID
    python learn_bandit.py --stage sealed --run-id RUN_ID-sealed
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import traceback
from typing import Any

import numpy as np

from bandit import (
    LLMPicker, ThompsonPolicy, bandit_evidence, explore, hit, jev_pick, jev_scores, lift, llm_picks,
    observe, regret, router_tau,
)
from candidates import (
    InvalidCandidate, apply_candidate, candidate_prompt, candidate_schema, changed_question, describe,
    is_near_duplicate, signature, validate_version,
)
from deciders import RubricQuestion
from editor import make_rewordings
from gate import best_passing, gate_version
from llm_factory import build_jev_client, build_llm_client
from log import JsonlLogger
from openrouter_llm import ContentBlockedError
from spend import SpendTracker
from telemetry import Telemetry
from verdict_bandit import compute_bandit_verdict
from workspace import Workspace

ARMS = {"R": "Jev + LLM router", "L": "LLM only", "J": "Jev only"}

GUIDANCE = """

THIS IS PARTIAL FEEDBACK. For each test you only see the click rate of the headline this policy chose.
You never see how the other headlines did, or which one was best. Click rates also differ a lot between
stories, so one low click rate may just be a weak story. Look for patterns across many tests: which kinds of
chosen headlines earned higher click rates, and whether exploration picks (a random other headline, tried on
purpose) did better or worse than the policy's own picks."""


def load_tests(ws: Workspace, set_name: str) -> list[dict]:
    return [json.loads(line) for line in (ws.path("pairs") / f"{set_name}.jsonl").read_text().splitlines()]


class Policies:
    """Makes decisions for any arm, with caching of LLM and Jev work."""

    def __init__(self, ws: Workspace, llm, jev, logger, telemetry, run_id: str, fixed_llm_instructions: str):
        self.ws, self.config = ws, ws.config
        self.llm, self.jev, self.logger, self.telemetry, self.run_id = llm, jev, logger, telemetry, run_id
        self.picker = LLMPicker(llm, ws.wording)
        self.fixed_llm_instructions = fixed_llm_instructions
        self._llm_cache: dict[tuple[str, str], dict] = {}
        self._lock = threading.Lock()

    def llm_for(self, instructions: str, tests: list[dict], set_name: str, lane: str, version_id: str) -> dict[str, dict]:
        missing = [t for t in tests if (instructions, t["test_id"]) not in self._llm_cache]
        if missing:
            got = llm_picks(self.picker, instructions, missing, batch_size=self.config["api"]["batch_size"],
                            workers=self.config["api"]["llm_workers"], seed=self.config["seed"],
                            event={"run_id": self.run_id, "loop": lane, "set": set_name, "version_id": version_id,
                                   "call_type": "decision_batch"},
                            progress=lambda **v: self.telemetry.stage(lane, stage="llm", set=set_name,
                                                                        version_id=version_id, **v))
            with self._lock:
                for test_id, value in got.items():
                    self._llm_cache[(instructions, test_id)] = value
        return {t["test_id"]: self._llm_cache[(instructions, t["test_id"])] for t in tests}

    def decide(self, arm: str, policy: dict, tests: list[dict], *, set_name: str, round_number: Any,
               exploration: bool) -> list[dict]:
        seed = self.config["seed"]
        version_id = policy["version_id"]
        lane = arm
        scored = None
        if arm in ("R", "J"):
            scored = jev_scores(self.jev, policy["rubric_questions"], policy.get("weights"), tests,
                                workers=self.config["api"]["jev_workers"],
                                event={"run_id": self.run_id, "loop": arm, "round": round_number, "set": set_name,
                                       "version_id": version_id, "call_type": "rubric_evaluation"},
                                progress=lambda **v: self.telemetry.stage(lane, stage="jev", set=set_name,
                                                                            version_id=version_id, round=round_number, **v))
        llm = None
        if arm == "L":
            llm = self.llm_for(policy["instructions"], tests, set_name, lane, version_id)
        tau = None
        if arm == "R":
            margins = {t["test_id"]: jev_pick(t, scored[t["test_id"]], seed)[1] for t in tests}
            tau = router_tau(list(margins.values()), self.config["router"]["llm_share"])
            # LLM picks are requested for every test in fixed batch order (stable disk cache
            # across restarts); only routed tests are charged below.
            llm = self.llm_for(self.fixed_llm_instructions, tests, set_name, lane, "R-llm")
        decisions = []
        for test in tests:
            tid = test["test_id"]
            decided_by, reason, blocked, cost, latency = "jev", None, False, 0.0, 0.0
            if scored is not None:
                greedy, margin = jev_pick(test, scored[tid], seed)
                cost += scored[tid]["cost"]
                latency += scored[tid]["latency_ms"]
            if arm == "L" or (arm == "R" and margin < tau):
                entry = llm[tid]
                decided_by, reason, blocked = "llm", entry["reason"], entry["blocked"]
                cost += entry["cost"]
                latency += entry["latency_ms"]
                if not (arm == "R" and blocked):  # router falls back to Jev on a refused test
                    greedy = entry["pick"]
                else:
                    decided_by = "jev"
            pick, explored = (explore(test, greedy, rate=self.config["learning"]["exploration_rate"], seed=seed,
                                      round_number=round_number) if exploration else (greedy, False))
            decisions.append({
                "test_id": tid, "pick": pick, "greedy_pick": greedy, "explored": explored,
                "decided_by": decided_by, "reason": reason, "blocked": blocked, "cost": cost, "latency_ms": latency,
                "chosen_probs": scored[tid]["probs"][pick] if scored is not None else None,
            })
        return decisions


def feedback(arm: str, policy: dict, tests: list[dict], decisions: list[dict], *, count: int, seed: int,
             round_number: int, attempt: int = 1) -> dict:
    """What the editor may see: chosen headlines and their observed click rates only."""
    by_id = {t["test_id"]: t for t in tests}
    for d in decisions:
        d["observed"] = observe(by_id[d["test_id"]], d["pick"])
    own = [d for d in decisions if not d["explored"]]
    explored = [d for d in decisions if d["explored"]]
    rng = random.Random(f"{seed}:{arm}:{round_number}:{attempt}:feedback")
    lowest = sorted(own, key=lambda d: d["observed"]["ctr"])[: count // 2]
    sample = lowest + rng.sample(explored, min(count - len(lowest), len(explored)))
    shown = []
    for d in sorted(sample, key=lambda d: d["test_id"]):
        test = by_id[d["test_id"]]
        entry = {"test_id": d["test_id"],
                 "headlines": {str(i + 1): h for i, h in enumerate(test["headlines"])},
                 "chosen": d["pick"] + 1, "exploration_pick": d["explored"],
                 "observed_click_rate_pct": round(100 * d["observed"]["ctr"], 3),
                 "impressions": d["observed"]["impressions"]}
        if arm == "R":
            entry["decided_by"] = d["decided_by"]
        if d["reason"] and not d["explored"]:
            entry["decider_reason"] = d["reason"]
        shown.append(entry)
    mean = lambda rows: round(100 * float(np.mean([r["observed"]["ctr"] for r in rows])), 3) if rows else None
    out = {"tests_this_round": len(decisions),
           "mean_click_rate_pct_own_picks": mean(own), "mean_click_rate_pct_exploration_picks": mean(explored),
           "sampled_tests": shown}
    if arm == "R":
        out["mean_click_rate_pct_by_decider"] = {
            name: mean([d for d in own if d["decided_by"] == name]) for name in ("jev", "llm")}
    if arm in ("R", "J"):
        out["bandit_evidence_table"] = bandit_evidence(decisions, policy["rubric_questions"])
    return out


def gate_outcome(tests: list[dict], old: list[dict], new: list[dict], threshold: float):
    """Compare two policies by the observed click rates of their own greedy picks."""
    by_id = {t["test_id"]: t for t in tests}
    old_ok, new_ok = [], []
    for o, n in zip(old, new):
        if o["pick"] == n["pick"]:
            old_ok.append(True); new_ok.append(True)
            continue
        oc, nc = observe(by_id[o["test_id"]], o["pick"])["ctr"], observe(by_id[n["test_id"]], n["pick"])["ctr"]
        old_ok.append(oc >= nc); new_ok.append(nc >= oc)
    return gate_version(old_ok, new_ok, p_threshold=threshold)


class Arm:
    def __init__(self, arm: str, ws: Workspace, policies: Policies, version0: dict, *, stop: threading.Event):
        self.arm, self.ws, self.config, self.p, self.stop = arm, ws, ws.config, policies, stop
        self.loop = "A" if arm == "L" else "B"  # which file the editor edits
        self.current = {"version_id": f"{arm}-v0",
                        **({"instructions": version0["instructions"]} if arm == "L"
                           else {"rubric_questions": version0["rubric_questions"]})}
        self.version0 = dict(self.current)
        self.history: list[dict] = []
        self.rejected: list[str] = []
        self.kept = 0
        self.proposed = 0

    def owned(self, policy: dict) -> dict:
        return {k: v for k, v in policy.items() if k in ("instructions", "rubric_questions")}

    def question_check(self, question: dict, practice: list[dict], round_number: int, candidate_id: str) -> bool:
        learning = self.config["learning"]
        headlines = [h for t in practice for h in t["headlines"]][: learning["question_check_items"]]
        for attempt in (1, 2):
            texts = make_rewordings(question=question, client=self.p.llm, item_scope=self.ws.wording["item_scope"],
                                    event={"run_id": self.p.run_id, "loop": "editor", "round": round_number,
                                           "version_id": candidate_id, "call_type": "question_rewording",
                                           "attempt": attempt, "target_loop": self.arm})
            variants = [RubricQuestion(question["question_id"], text, question["direction"]) for text in texts]
            disagreements = 0
            for index, headline in enumerate(headlines):
                answers = [self.p.jev.evaluate(headline, [v], {"run_id": self.p.run_id, "loop": self.arm,
                                                               "call_type": "question_check", "pair_id": f"qc-{index}",
                                                               "version_id": candidate_id, "wording": w},
                                               use_cache=False)[question["question_id"]]
                           for w, v in enumerate(variants, start=1)]
                disagreements += int((answers[0] >= 0.5) != (answers[1] >= 0.5))
            if disagreements <= learning["question_check_max_disagreements"]:
                return True
        return False

    def propose(self, fb: dict, round_number: int) -> list[dict]:
        prompt = candidate_prompt(loop=self.loop, current=self.owned(self.current), feedback=fb, history=self.history,
                                  rejected=self.rejected, config=self.config, wording=self.ws.wording, guidance=GUIDANCE)
        return self.p.llm.generate_json(prompt=prompt, schema=candidate_schema(self.loop, self.config),
                                        event={"run_id": self.p.run_id, "loop": "editor", "round": round_number,
                                               "version_id": self.current["version_id"],
                                               "call_type": "candidate_proposal", "target_loop": self.arm})["candidates"]

    def run(self, practice: list[dict], gate: list[dict]) -> dict:
        learning, seed = self.config["learning"], self.config["seed"]
        telemetry = self.p.telemetry
        gate_current = self.p.decide(self.arm, self.current, gate, set_name="gate", round_number=0, exploration=False)
        for round_number in range(1, learning["rounds"] + 1):
            if self.stop.is_set():
                raise RuntimeError("stopped because another arm failed")
            batch = practice[(round_number - 1) * learning["batch"]: round_number * learning["batch"]]
            decisions = self.p.decide(self.arm, self.current, batch, set_name="practice", round_number=round_number,
                                      exploration=True)
            proposals: list[dict] = []
            for attempt in (1, 2, 3):
                fb = feedback(self.arm, self.current, batch, decisions, count=learning["feedback_tests"], seed=seed,
                              round_number=round_number, attempt=attempt)
                try:
                    proposals = self.propose(fb, round_number)
                    break
                except ContentBlockedError:
                    telemetry.note(f"{self.arm} round {round_number}: editor prompt blocked (attempt {attempt})")
            telemetry.evaluation(loop=self.arm, round_number=round_number, set_name="practice",
                                 version_id=self.current["version_id"],
                                 summary={"tests": len(batch), "observed_mean_click_rate_pct_own": fb["mean_click_rate_pct_own_picks"],
                                          "observed_mean_click_rate_pct_exploration": fb["mean_click_rate_pct_exploration_picks"]})
            gated, versions, sigs = [], {}, []
            for index, proposal in enumerate(proposals[: learning["max_changes"]], start=1):
                self.proposed += 1
                cid = f"{self.arm}-r{round_number}-c{index}"
                record = {"arm": self.arm, "round": round_number, "candidate_id": cid,
                          "based_on": self.current["version_id"], "reason": " ".join(str(proposal.get("reason", "")).split())}
                try:
                    record["change"] = describe(self.loop, proposal)
                    sig = signature(self.loop, proposal)
                    if is_near_duplicate(sig, self.rejected + sigs, learning["duplicate_similarity"]):
                        record["status"] = "refused_duplicate_of_rejected"
                    else:
                        sigs.append(sig)
                        new = apply_candidate(self.loop, self.owned(self.current), proposal, self.config)
                        validate_version(self.loop, new, self.config)
                        question = changed_question(self.loop, proposal, new)
                        if question is not None and not self.question_check(question, batch, round_number, cid):
                            record["status"] = "failed_question_check"
                            self.rejected.append(sig)
                        else:
                            version = {"version_id": cid, **new}
                            gate_new = self.p.decide(self.arm, version, gate, set_name="gate",
                                                     round_number=round_number, exploration=False)
                            outcome = gate_outcome(gate, gate_current, gate_new, learning["gate_p_threshold"])
                            gated.append((cid, outcome))
                            versions[cid] = (version, gate_new, record, sig)
                            record.update(b=outcome.b, c=outcome.c, p=round(outcome.p_value, 6), passed=outcome.keep)
                            record["status"] = "gated"
                except (InvalidCandidate, ValueError, KeyError) as error:
                    record["status"], record["error"] = "invalid", str(error)
                if record["status"] != "gated":
                    self.history.append(record)
                    telemetry.candidate(record)
            winner = best_passing(gated)
            for cid, _ in gated:
                version, gate_new, record, sig = versions[cid]
                record["kept"] = cid == winner
                record["status"] = "kept" if record["kept"] else ("passed_not_best" if record["passed"] else "rejected")
                if not record["kept"]:
                    self.rejected.append(sig)
                self.history.append(record)
                telemetry.candidate(record)
                self.p.logger.write({**record, "call_type": "gate", "run_id": self.p.run_id})
            telemetry.gate({"loop": self.arm, "round": round_number, "kept": winner, "proposed": len(proposals),
                            "results": {cid: {"b": o.b, "c": o.c, "p": round(o.p_value, 6)} for cid, o in gated}})
            if winner is not None:
                self.current, gate_current = versions[winner][0], versions[winner][1]
                self.kept += 1
                telemetry.current(self.arm, self.current)
        telemetry.finish(self.arm, kept=self.kept)
        return self.current


def thompson_learn(ws: Workspace, practice: list[dict]) -> tuple[ThompsonPolicy, list[dict]]:
    cfg, learning = ws.config["thompson"], ws.config["learning"]
    policy = ThompsonPolicy(cfg["prior_variance"], cfg["noise_variance"], ws.config["seed"])
    rounds = []
    for r in range(1, learning["rounds"] + 1):
        batch = practice[(r - 1) * learning["batch"]: r * learning["batch"]]
        picks = [policy.pick(t, sample=True, round_number=r) for t in batch]
        observed = [(t["headlines"][p], observe(t, p)["ctr"]) for t, p in zip(batch, picks)]
        policy.update(observed)
        rounds.append({"round": r, "observed_mean_click_rate_pct": round(100 * float(np.mean([c for _, c in observed])), 3)})
    return policy, rounds


def setup(ws: Workspace, run_id: str):
    results, logs = ws.path("results"), ws.path("logs")
    spend = SpendTracker(results / "spend.json", ws.config["budget"]["spend_cap_usd"])
    telemetry = Telemetry(results, run_id, spend)
    logger = JsonlLogger(logs / f"{run_id}.jsonl")
    llm = build_llm_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend)
    jev = build_jev_client(ws.config, ws.root, run_id, logs_dir=logs, spend=spend)
    version0 = json.loads((ws.root / ws.config["components"]["version0"]).read_text())
    policies = Policies(ws, llm, jev, logger, telemetry, run_id, fixed_llm_instructions=version0["instructions"])
    return spend, telemetry, policies, version0


def stage_learn(ws: Workspace, run_id: str) -> None:
    results = ws.path("results")
    frozen_path = results / "final_versions.json"
    if frozen_path.exists():
        raise RuntimeError("final versions already frozen; refusing to rerun learning")
    spend, telemetry, policies, version0 = setup(ws, run_id)
    practice, gate = load_tests(ws, "practice"), load_tests(ws, "gate")
    stop = threading.Event()
    arms = {name: Arm(name, ws, policies, version0, stop=stop) for name in ARMS}
    finals, errors = {}, {}

    def work(name):
        try:
            finals[name] = arms[name].run(practice, gate)
        except Exception as error:
            errors[name] = f"{type(error).__name__}: {error}"
            stop.set()
            telemetry.stage(name, stage="failed", error=errors[name])
            traceback.print_exc()

    threads = [threading.Thread(target=work, args=(n,)) for n in ARMS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    spend.flush()
    if errors:
        raise RuntimeError(f"learning failed: {errors}")
    thompson, thompson_rounds = thompson_learn(ws, practice)
    frozen = {"frozen": True, "run_id": run_id, "arms": ARMS,
              "version0": {n: a.version0 for n, a in arms.items()}, "final": finals,
              "history": {n: a.history for n, a in arms.items()},
              "edits": {n: {"proposed": a.proposed, "kept": a.kept} for n, a in arms.items()},
              "thompson": {"weights": thompson.mean().tolist(), "precision": thompson.precision.tolist(),
                           "b": thompson.b.tolist(), "rounds": thompson_rounds},
              "notes": {"learning_paid_spend_usd": round(spend.total_usd, 4)}}
    frozen_path.write_text(json.dumps(frozen, indent=2) + "\n")
    telemetry.note("learning complete; final versions frozen")
    print(json.dumps(frozen["edits"]))


def stage_sealed(ws: Workspace, run_id: str) -> None:
    results = ws.path("results")
    completed = results / "sealed_complete.json"
    if completed.exists():
        raise RuntimeError("sealed evaluation already completed; refusing to rerun")
    frozen = json.loads((results / "final_versions.json").read_text())
    if frozen.get("frozen") is not True:
        raise RuntimeError("final versions are not frozen")
    spend, telemetry, policies, _ = setup(ws, run_id)
    sealed = load_tests(ws, "sealed")
    systems = {}
    for arm in ARMS:
        for label, policy in (("version0", frozen["version0"][arm]), ("final", frozen["final"][arm])):
            systems[f"{arm}_{label}"] = policies.decide(arm, policy, sealed, set_name="sealed",
                                                        round_number="final", exploration=False)
    # Router with both components learned: R's final rubric + L's final instructions.
    policies.fixed_llm_instructions = frozen["final"]["L"]["instructions"]
    systems["R_final_with_L_final"] = policies.decide("R", frozen["final"]["R"], sealed, set_name="sealed",
                                                     round_number="final", exploration=False)
    thompson = ThompsonPolicy(ws.config["thompson"]["prior_variance"], ws.config["thompson"]["noise_variance"],
                              ws.config["seed"])
    thompson.precision, thompson.b = np.array(frozen["thompson"]["precision"]), np.array(frozen["thompson"]["b"])
    systems["C_final"] = [{"test_id": t["test_id"], "pick": thompson.pick(t, sample=False, round_number=0), "cost": 0.0,
                           "latency_ms": 0.0, "decided_by": "thompson", "blocked": False} for t in sealed]
    by_id = {t["test_id"]: t for t in sealed}
    metrics = {}
    for name, decisions in systems.items():
        metrics[name] = {
            "lift": [lift(by_id[d["test_id"]], d["pick"]) for d in decisions],
            "regret": [regret(by_id[d["test_id"]], d["pick"]) for d in decisions],
            "hit": [hit(by_id[d["test_id"]], d["pick"]) for d in decisions],
            "cost_per_1000": sum(d["cost"] for d in decisions) / len(decisions) * 1000,
            "latency_ms": sum(d["latency_ms"] for d in decisions) / len(decisions),
            "llm_share": sum(d["decided_by"] == "llm" for d in decisions) / len(decisions),
            "blocked": sum(bool(d.get("blocked")) for d in decisions),
        }
    oracle_lift = [lift(t, int(np.argmax(t["ctr"]))) for t in sealed]
    random_hit = float(np.mean([1 / len(t["headlines"]) for t in sealed]))
    verdict = compute_bandit_verdict(metrics=metrics, config=ws.config["verdict"],
                                     max_cost_ratio=ws.config["router"]["max_cost_ratio"])
    spend.flush()
    summary = {name: {"mean_lift_pts": float(np.mean(m["lift"])), "mean_regret": float(np.mean(m["regret"])),
                      "hit_rate": float(np.mean(m["hit"])), "cost_per_1000": m["cost_per_1000"],
                      "avg_latency_ms": m["latency_ms"], "llm_share": m["llm_share"], "blocked": m["blocked"]}
               for name, m in metrics.items()}
    result = {"run_id": run_id, "verdict": verdict, "summary": summary,
              "references": {"random_pick": {"mean_lift_pts": 0.0, "hit_rate": random_hit},
                             "best_headline": {"mean_lift_pts": float(np.mean(oracle_lift)), "hit_rate": 1.0}},
              "edits": frozen["edits"], "thompson_rounds": frozen["thompson"]["rounds"],
              "paid_spend_usd_total_experiment6": round(spend.total_usd, 4)}
    completed.write_text(json.dumps(result, indent=2) + "\n")
    telemetry.finish("sealed", verdict=verdict["verdict"])
    print(json.dumps({k: result[k] for k in ("verdict", "summary", "references")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment 6: learning from partial feedback.")
    parser.add_argument("--stage", choices=("learn", "sealed"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", default="config_upworthy6.yaml")
    parser.add_argument("--task", default="task_upworthy6.yaml")
    args = parser.parse_args()
    ws = Workspace.load(args.config, args.task)
    (stage_learn if args.stage == "learn" else stage_sealed)(ws, args.run_id)


if __name__ == "__main__":
    main()
