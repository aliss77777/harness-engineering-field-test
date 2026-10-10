"""The v2 Phase 1 experiments (briefs/Phase 1 design.md; briefs/Skill loop redesign.md).

    .venv/bin/python scripts/phase1_run.py skill    # Agent skill loop: MiniMax edits its own playbook (checkpoint on)
    .venv/bin/python scripts/phase1_run.py skill --stop-after-round 2   # same, but stop (resumably) once round 2 is saved
    .venv/bin/python scripts/phase1_run.py replay-refused  # test the rules refused for length in rounds 3-4 (limit now 1,200); changes nothing else
    .venv/bin/python scripts/phase1_run.py jevdata  # MiniMax's final playbook on practice + test bench (Jev's learning data)
    .venv/bin/python scripts/phase1_run.py rubric   # Jev rubric loop: MiniMax edits Jev's questions; v1's McNemar test
    .venv/bin/python scripts/phase1_run.py tau      # the Router's threshold, frozen on the test bench
    .venv/bin/python scripts/phase1_run.py sealed   # the final exam, once (needs Alexander's written release)

Safety: every paid stage refuses to run unless phase1/config_phase1.yaml has run.approved: true; the spend
cap is enforced in code; the sealed stage needs phase1/SEALED_RELEASE.md; every run is logged and reloaded,
so a stop resumes without paying twice. Outputs go to phase1/run/take<N>/ (N = run.take in the config; Take 1 used
the p-value keep test, Take 2 the margin keep test); run logs are shared across takes, so identical runs are reused.
"""
import argparse
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scipy.stats import wilcoxon  # noqa: E402

from jevloop import bench, evalstats  # noqa: E402
from jevloop.cache import DiskCache  # noqa: E402
from jevloop.cascade import route, set_tau, v2_3_verdict  # noqa: E402
from jevloop.diagnostics import behaviour  # noqa: E402
from jevloop.feasibility import paired_bootstrap_interval  # noqa: E402
from jevloop.jev import JevClient  # noqa: E402
from jevloop.llm_agent import LLMAgent  # noqa: E402
from jevloop.log import JsonlLogger  # noqa: E402
from jevloop.masking import verdict as checkpoint_verdict  # noqa: E402
from jevloop.monitor import ReadPoliciesFirst, company_data  # noqa: E402
from jevloop.openrouter import ChatClient  # noqa: E402
from jevloop.rubric import (STARTING_RUBRIC, Question, RubricEdit, apply_rubric_edit, check_rubric_edit, classify,  # noqa: E402
                            fit_weights, is_good, keep_rubric_edit, parse_rubric_edits, rubric_editor_prompt, score)
from jevloop.runs import CandidateRun, run_candidate  # noqa: E402
from jevloop.skill_loop import (Edit, SkillEditor, apply_edit, failure_profile, keep_rule, length_refused_edits,  # noqa: E402
                                mistakes_report, skill_text, version_id)
from jevloop.spend import SpendTracker  # noqa: E402
from jevloop.verifier import (COMPLIANCE_WRITER, build_state, make_questions, policy_text, verifier_score)  # noqa: E402

CFG1 = yaml.safe_load((ROOT / "phase1" / "config_phase1.yaml").read_text())
CFG0 = yaml.safe_load((ROOT / "phase0" / "config_phase0.yaml").read_text())
RUN = CFG1["run"]
OUT = ROOT / "phase1" / "run" / f"take{RUN.get('take', 1)}"
LOGS = ROOT / "logs" / "phase1_run"
SPLITS = ROOT / "phase1" / "splits"


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_KEY missing")


def split(name: str) -> list[str]:
    return (SPLITS / f"{name}.txt").read_text().split()


def save(name: str, data) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")


def load_json(name: str):
    path = OUT / f"{name}.json"
    if not path.exists():
        sys.exit(f"{path.relative_to(ROOT)} missing: run the earlier stage first")
    return json.loads(path.read_text())


def merged(runs: list[CandidateRun]) -> CandidateRun:
    """Several runs of one task as one record for the keep-or-reject test: mean credit, all checks pooled."""
    if len(runs) == 1:
        return runs[0]
    r0 = runs[0]
    fields = {k: getattr(r0, k) for k in CandidateRun.__dataclass_fields__}
    fields.update(partial_credit=sum(r.partial_credit for r in runs) / len(runs), passed=all(r.passed for r in runs),
                  checks=[c for r in runs for c in r.checks], holds=sum(r.holds for r in runs), cost_usd=sum(r.cost_usd for r in runs))
    return CandidateRun(**fields)


class Phase1:
    def __init__(self, *, paid: bool = True):
        if paid and not RUN.get("approved"):
            sys.exit("STOP: v2 Phase 1 is not approved yet (phase1/config_phase1.yaml run.approved is false). Ask Alexander.")
        # PHASE1_SPEND_FILE lets two stages run side by side without overwriting each other's accounting
        self.spend = SpendTracker(ROOT / "results" / "phase1_run" / os.environ.get("PHASE1_SPEND_FILE", "spend.json"),
                                  cap_usd=RUN["spend_cap_usd"], flush_seconds=0)
        key = api_key()
        cache = DiskCache(ROOT / "cache" / "openrouter")
        calls = JsonlLogger(LOGS / "calls.jsonl")

        def chat(name: str, temperature: float) -> ChatClient:
            m = CFG0["models"][name]
            return ChatClient(model=m["model"], provider=m["provider"], provider_tag=m["provider_tag"], expected_model=m["expected_model"],
                              api_key=key, cache=cache, logger=calls, spend=self.spend, temperature=temperature,
                              reasoning_effort=CFG0["reasoning_effort"], retries=CFG0["retries"])

        self.minimax = chat("minimax", RUN["agent_temperature"])
        self.gemini = chat("gemini", RUN["agent_temperature"])
        self.editor_client = chat("minimax", RUN["editor_temperature"])
        j = CFG1["jev"]
        self.jev = JevClient(model=j["model"], expected_model=j["expected_model"], expected_provider=j["expected_provider"], api_key=key,
                             cache=DiskCache(ROOT / "cache" / "jev"), logger=JsonlLogger(LOGS / "jev-calls.jsonl"), spend=self.spend)
        self.tasks = {t.task_id: t for t in bench.load_tasks(CFG1["domains"])}
        self.data = {t: company_data(task.initial_state) for t, task in self.tasks.items()}

    def guard(self, runs: int, model: str) -> None:
        projected = runs * RUN["cost_estimate_per_run"][model]
        if self.spend.total_usd + projected > self.spend.cap_usd:
            sys.exit(f"STOP: {runs} {model} runs (≈ ${projected:.2f}) would pass the ${self.spend.cap_usd:.2f} cap "
                     f"(spent ${self.spend.total_usd:.2f}). Ask Alexander.")

    def run_set(self, *, model: str, rules: tuple[str, ...], checkpoint: bool, task_ids: list[str], label: str,
                runs_per_task: int = 1, first_attempt: int = 0) -> dict[str, list[CandidateRun]]:
        vid = version_id(rules)
        name = f"{model}-p1-{vid}-{'cp' if checkpoint else 'nocp'}"
        path = LOGS / f"{name}-{label}.jsonl"
        done: dict[tuple[str, int], CandidateRun] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                r = json.loads(line)
                done[(r["task_id"], r["candidate"])] = CandidateRun(**{k: v for k, v in r.items() if k in CandidateRun.__dataclass_fields__})
        jobs = [(t, a) for t in task_ids for a in range(first_attempt, first_attempt + runs_per_task) if (t, a) not in done]
        self.guard(len(jobs), model)
        client = self.minimax if model == "minimax" else self.gemini
        agent = LLMAgent(name, client, max_steps=CFG0["max_steps"], skill=skill_text(rules) if rules else None,
                         monitor=ReadPoliciesFirst() if checkpoint else None, company_data=self.data if checkpoint else None)
        logger = JsonlLogger(path)

        def one(job):
            t, a = job
            run = run_candidate(self.tasks[t], agent, a)
            logger.write({"event": "candidate_run", "run_id": f"{name}-{label}", **run.record()})
            return run

        if jobs:
            print(f"  {name} on {label}: {len(done)} reloaded, running {len(jobs)}", flush=True)
            with ThreadPoolExecutor(max_workers=RUN["workers"]) as pool:
                for run in pool.map(one, jobs):
                    done[(run.task_id, run.candidate)] = run
            self.spend.flush()
            print(f"  {name} on {label}: done; spend ${self.spend.total_usd:.2f}", flush=True)
        return {t: [done[(t, a)] for a in range(first_attempt, first_attempt + runs_per_task)] for t in task_ids}

    def jev_probs(self, questions: tuple[Question, ...], runs: dict[str, CandidateRun], label: str) -> dict[str, dict[str, float]]:
        """Jev reads only each run's summary (never the grading checks)."""
        self.guard(len(runs), "jev_call")
        return {t: self.jev.evaluate(r.summary, list(questions), {"event": "jev_rubric", "label": label, "task_id": t})["probabilities"]
                for t, r in runs.items()}


# ---------------- stage 1: the Agent skill loop (checkpoint on during learning) ----------------

def stage_skill(args) -> None:
    p = Phase1()
    s = RUN["skill_loop"]
    cp = RUN["checkpoint_during_learning"]
    practice, bench_ids = split("practice"), split("gate")[: s["test_bench_tasks"]]
    editor = SkillEditor(p.editor_client)
    rules: tuple[str, ...] = ()
    rejected: list[Edit] = []
    history = []
    for rnd in range(1, s["rounds"] + 1):
        print(f"SKILL ROUND {rnd}: version {version_id(rules)} ({len(rules)} rules)", flush=True)
        sample = sorted(random.Random(f"{CFG1['seed']}:p1:practice:{rnd}").sample(practice, s["practice_per_round"]))
        prac = {t: rs[0] for t, rs in p.run_set(model="minimax", rules=rules, checkpoint=cp, task_ids=sample, label=f"practice-r{rnd}").items()}
        behaviours = [behaviour(p.tasks[t], r.calls, r.missed_checks) for t, r in prac.items()]
        profile = failure_profile(list(prac.values()), behaviours)
        mistakes = mistakes_report(list(prac.values()), limit=s["mistakes_shown"], rng=random.Random(f"{CFG1['seed']}:p1:mistakes:{rnd}"))
        edits, refused = editor.propose(rules, mistakes, rejected, n=s["candidates_per_round"], round_number=1000 + rnd, profile=profile)
        current = {t: merged(rs) for t, rs in p.run_set(model="minimax", rules=rules, checkpoint=cp, task_ids=bench_ids,
                                                         label="bench", runs_per_task=s["runs_per_task"]).items()}
        decisions = []
        for e in edits:
            cand = {t: merged(rs) for t, rs in p.run_set(model="minimax", rules=apply_edit(rules, e), checkpoint=cp, task_ids=bench_ids,
                                                          label="bench", runs_per_task=s["runs_per_task"]).items()}
            d = keep_rule(current, cand, kind=e.target, regression=[], p_threshold=s["p_threshold"], max_regression_drop=s["max_regression_drop"],
                          test=s.get("keep_test", "p_value"), min_credit_gain=s.get("min_credit_gain", 0.02))
            decisions.append((e, d))
            print(f"    {e.target:13} {d.targeted_diff:+.3f} p {d.targeted_p:.3f} net {d.net_diff:+.3f} passes {d.passes_diff:+d} "
                  f"-> {'KEEP' if d.keep else 'reject'} ({s.get('keep_test', 'p_value')} test): {e.text[:70]}", flush=True)
        kept = [(e, d) for e, d in decisions if d.keep]
        winner = max(kept, key=lambda ed: ed[1].targeted_diff)[0] if kept else None
        rejected += [e for e, _ in decisions if e is not winner]
        before = rules
        if winner:
            rules = apply_edit(rules, winner)
        history.append({"round": rnd, "rules_before": list(before), "profile": profile, "edits": [e.record() for e in edits],
                        "refused": refused, "decisions": [{"edit": e.record(), "decision": d.record()} for e, d in decisions],
                        "kept": winner.record() if winner else None, "rules_after": list(rules), "spend_usd": p.spend.total_usd})
        save("skill_history", history)
        stop_at = getattr(args, "stop_after_round", None)
        if stop_at and rnd == stop_at and rnd < s["rounds"]:
            print(f"STOPPED after round {rnd} as asked (Take {RUN.get('take', 1)}); run `skill` again to resume (finished runs are reloaded).", flush=True)
            return
    save("skill_final", {"rules": list(rules), "version": version_id(rules), "checkpoint_during_learning": cp})
    print(f"final playbook {version_id(rules)}: {len(rules)} rules; spend ${p.spend.total_usd:.2f}", flush=True)


def verifier_scores(p, runs: dict[str, CandidateRun], *, sets: int = 3) -> dict[str, float]:
    """Jev redesign, second attempt, variant 3 (scripts/jev_verifier_d2.py, validated once, bar met): the mean over
    `sets` independent question sets, averaged with a policy-compliance question set. Jev reads the request, the
    policy emails, the source records read, the writes in full and the diff; never the grader's checks."""
    instructions = (OUT / "verifier_instructions_final.txt").read_text().strip()
    tasks = sorted(runs)

    def questions(client, text, tag):
        return {t: make_questions(client, text, t, p.tasks[t].public.trigger, policy_text(p.tasks[t].initial_state), tag=tag) for t in tasks}
    sample_sets = [questions(p.editor_client, instructions, f"d2s{k}") for k in range(sets)]
    compliance = questions(p.minimax, COMPLIANCE_WRITER, "d2compliance")
    out = {}
    for t in tasks:
        task, r = p.tasks[t], runs[t]
        state = build_state(task.public.trigger, task.initial_state, r.calls, r.summary)

        def mean_p(qs, tag):
            return verifier_score(p.jev.evaluate(state, qs, {"event": "sealed_verifier", "tag": tag, "task_id": t})["probabilities"])
        v2 = sum(mean_p(sample_sets[k][t], f"s{k}") for k in range(sets)) / sets
        out[t] = 0.5 * v2 + 0.5 * mean_p(compliance[t], "compliance")
    return out


def stage_replay_refused(_args) -> None:
    """Test, as written, the rules the loop refused for length in Take 2's rounds 3-4 (the 600-character limit was
    raised to 1,200 on 2026-10-10). Each is added to the final playbook and tried on the test bench against it,
    one run per task, with the same margin keep test. Writes phase1/run/take<N>/skill_replay.json only; it does
    not change skill_final.json (that waits for Alexander)."""
    p = Phase1()
    s = RUN["skill_loop"]
    cp = RUN["checkpoint_during_learning"]
    final = tuple(load_json("skill_final")["rules"])
    history = load_json("skill_history")
    refused = length_refused_edits(history, from_round=3)
    bench_ids = split("gate")[: s["test_bench_tasks"]]
    current = {t: merged(rs) for t, rs in p.run_set(model="minimax", rules=final, checkpoint=cp, task_ids=bench_ids,
                                                     label="bench", runs_per_task=s["runs_per_task"]).items()}
    mean = lambda d: sum(r.partial_credit for r in d.values()) / len(d)  # noqa: E731
    passes = lambda d: sum(r.passed for r in d.values())  # noqa: E731
    print(f"REPLAY: {len(refused)} length-refused rules against playbook {version_id(final)} "
          f"({mean(current):.3f} credit, {passes(current)} passes)", flush=True)
    results = []
    for e in refused:
        cand = {t: merged(rs) for t, rs in p.run_set(model="minimax", rules=apply_edit(final, e), checkpoint=cp, task_ids=bench_ids,
                                                      label="bench", runs_per_task=s["runs_per_task"]).items()}
        d = keep_rule(current, cand, kind=e.target, regression=[], p_threshold=s["p_threshold"], max_regression_drop=s["max_regression_drop"],
                      test=s.get("keep_test", "p_value"), min_credit_gain=s.get("min_credit_gain", 0.02))
        results.append({"edit": e.record(), "length": len(e.text), "credit": mean(cand), "passes": passes(cand), "decision": d.record(),
                        "holds_per_run": sum(r.holds for r in cand.values()) / len(cand)})
        print(f"    {e.target:13} {len(e.text)} chars: credit {mean(cand):.3f} ({d.net_diff:+.3f}) passes {passes(cand)} ({d.passes_diff:+d}) "
              f"targeted {d.targeted_diff:+.3f} p {d.targeted_p:.3f} -> {'KEEP' if d.keep else 'reject'} ({s.get('keep_test', 'p_value')} test)", flush=True)
    kept = [x for x in results if x["decision"]["keep"]]
    winner = max(kept, key=lambda x: x["decision"]["targeted_diff"]) if kept else None
    save("skill_replay", {"baseline_version": version_id(final), "baseline_credit": mean(current), "baseline_passes": passes(current),
                          "max_rule_chars": 1200, "results": results, "winner": winner["edit"] if winner else None,
                          "proposed_rules": list(apply_edit(final, Edit(**winner["edit"]))) if winner else list(final),
                          "spend_usd": p.spend.total_usd})
    print(f"replay done; spend ${p.spend.total_usd:.2f}; kept {len(kept)} of {len(results)}", flush=True)


def _final_runs(p, cp: bool) -> dict[str, CandidateRun]:
    """The final playbook's one run per practice and test bench task (reloaded from the logs)."""
    final = tuple(load_json("skill_final")["rules"])
    out = {}
    for label, ids in (("practice-all", split("practice")), ("bench", split("gate"))):
        out.update({t: rs[0] for t, rs in p.run_set(model="minimax", rules=final, checkpoint=cp, task_ids=ids, label=label).items()})
    return out


def stage_ceiling(_args) -> None:
    """Gemini ceiling check (canonical design, follow-ups): Gemini, as it comes, on every practice and test bench task
    where the final playbook's MiniMax run scored under 0.8. Reports what a perfect failure detector could gain."""
    p = Phase1()
    mm = _final_runs(p, RUN["checkpoint_during_learning"])
    failed = sorted(t for t, r in mm.items() if r.partial_credit < 0.8)
    print(f"CEILING: {len(failed)} of {len(mm)} practice and test bench tasks scored under 0.8 with the final playbook", flush=True)
    gem = {t: rs[0] for t, rs in p.run_set(model="gemini", rules=(), checkpoint=False, task_ids=failed, label="ceiling").items()}
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    base = mean([r.partial_credit for r in mm.values()])
    worst30 = sorted(failed, key=lambda t: mm[t].partial_credit)[: round(0.3 * len(mm))]

    def routed(escalate: list[str]) -> float:
        return mean([gem[t].partial_credit if t in escalate else mm[t].partial_credit for t in mm])
    res = {"n_tasks": len(mm), "n_failed": len(failed), "minimax_alone": base,
           "on_failed_tasks": {"minimax": mean([mm[t].partial_credit for t in failed]), "gemini": mean([gem[t].partial_credit for t in failed]),
                               "gemini_passed": sum(gem[t].passed for t in failed)},
           "perfect_router_escalating_all_failures": {"share": len(failed) / len(mm), "credit": routed(failed)},
           "perfect_router_escalating_worst_30pct": {"share": len(worst30) / len(mm), "credit": routed(worst30)},
           "gemini_cost_per_run": mean([gem[t].cost_usd for t in failed]), "spend_usd": p.spend.total_usd}
    save("ceiling", res)
    print(json.dumps(res, indent=2), flush=True)


def stage_fresh(_args) -> None:
    """Two fresh, independent runs of the final playbook on every practice and test bench task (Jev verifier D2's data)."""
    p = Phase1()
    final = tuple(load_json("skill_final")["rules"])
    ids = split("practice") + split("gate")
    p.run_set(model="minimax", rules=final, checkpoint=RUN["checkpoint_during_learning"], task_ids=ids, label="fresh",
              runs_per_task=2, first_attempt=1)
    print(f"fresh runs ready; spend ${p.spend.total_usd:.2f}", flush=True)


# ---------------- stage 2: Jev's learning data ----------------

def stage_jevdata(_args) -> None:
    p = Phase1()
    final = tuple(load_json("skill_final")["rules"])
    cp = RUN["checkpoint_during_learning"]
    for label, ids in (("practice-all", split("practice")), ("bench", split("gate"))):
        p.run_set(model="minimax", rules=final, checkpoint=cp, task_ids=ids, label=label)
    print(f"Jev learning data ready; spend ${p.spend.total_usd:.2f}", flush=True)


# ---------------- stage 3: the Jev rubric loop ----------------

def _correct(probs, credits, questions, weights, b) -> dict[str, bool]:
    return {t: classify(probs[t], questions, weights, b) == is_good(credits[t]) for t in probs}


def stage_rubric(_args) -> None:
    p = Phase1()
    r = RUN["rubric_loop"]
    final = tuple(load_json("skill_final")["rules"])
    cp = RUN["checkpoint_during_learning"]
    prac = {t: rs[0] for t, rs in p.run_set(model="minimax", rules=final, checkpoint=cp, task_ids=split("practice"), label="practice-all").items()}
    bench_runs = {t: rs[0] for t, rs in p.run_set(model="minimax", rules=final, checkpoint=cp, task_ids=split("gate"), label="bench").items()}
    pc = {t: x.partial_credit for t, x in prac.items()}
    bc = {t: x.partial_credit for t, x in bench_runs.items()}

    def evaluate(questions):
        pp, bp = p.jev_probs(questions, prac, "practice"), p.jev_probs(questions, bench_runs, "bench")
        w, b = fit_weights([pp[t] for t in prac], [pc[t] for t in prac], questions, seed=CFG1["seed"])
        return pp, bp, w, b

    questions = STARTING_RUBRIC
    pp, bp, w, b = evaluate(questions)
    v0 = {"questions": [q.__dict__ for q in questions], "weights": w, "intercept": b}
    rejected: list[RubricEdit] = []
    history = []
    for rnd in range(1, r["rounds"] + 1):
        wrong = [t for t in prac if classify(pp[t], questions, w, b) != is_good(pc[t])]
        random.Random(f"{CFG1['seed']}:rubric:{rnd}").shuffle(wrong)
        mistakes = [{"run_summary": prac[t].summary[:2500], "judge_said": "good" if classify(pp[t], questions, w, b) else "bad",
                     "actually": "good" if is_good(pc[t]) else "bad", "credit": round(pc[t], 2),
                     "yes_probabilities": {k: round(v, 2) for k, v in pp[t].items()}} for t in wrong[: r["mistakes_shown"]]]
        reply = p.editor_client.complete(rubric_editor_prompt(questions, mistakes, rejected, r["candidates_per_round"]), [],
                                         cache_key={"editor": "rubric", "round": rnd}, event={"event": "rubric_editor", "round": rnd})
        try:
            proposals = parse_rubric_edits(reply["message"].get("content") or "")
        except Exception as error:  # noqa: BLE001
            proposals = []
            print(f"  rubric editor reply unparseable: {error}", flush=True)
        cands = [e for e in proposals if check_rubric_edit(e, questions, rejected) is None][: r["candidates_per_round"]]
        old_correct = _correct(bp, bc, questions, w, b)
        results = []
        for e in cands:
            q2 = apply_rubric_edit(questions, e)
            pp2, bp2, w2, b2 = evaluate(q2)
            new_correct = _correct(bp2, bc, q2, w2, b2)
            g = keep_rubric_edit([old_correct[t] for t in bc], [new_correct[t] for t in bc], p_threshold=r["p_threshold"])
            results.append((e, g, (q2, pp2, bp2, w2, b2)))
            print(f"  rubric round {rnd}: {e.op} {e.question_id} better {g.b} worse {g.c} p {g.p_value:.3f} -> {'KEEP' if g.keep else 'reject'}", flush=True)
        kept = [x for x in results if x[1].keep]
        winner = max(kept, key=lambda x: (x[1].b - x[1].c, -x[1].p_value)) if kept else None
        rejected += [e for e, _, _ in results if not (winner and e is winner[0])]
        if winner:
            questions, pp, bp, w, b = winner[2]
        history.append({"round": rnd, "candidates": [{"edit": e.record(), "better": g.b, "worse": g.c, "p": g.p_value, "keep": g.keep}
                                                     for e, g, _ in results], "kept": winner[0].record() if winner else None,
                        "bench_accuracy": sum(_correct(bp, bc, questions, w, b).values()) / len(bc)})
        save("rubric_history", history)
    save("rubric_final", {"questions": [q.__dict__ for q in questions], "weights": w, "intercept": b, "v0": v0})
    print(f"final rubric: {len(questions)} questions; spend ${p.spend.total_usd:.2f}", flush=True)


# ---------------- stage 4: the Router's threshold ----------------

def stage_tau(_args) -> None:
    p = Phase1()
    final = tuple(load_json("skill_final")["rules"])
    rb = load_json("rubric_final")
    questions = tuple(Question(**q) for q in rb["questions"])
    bench_runs = {t: rs[0] for t, rs in p.run_set(model="minimax", rules=final, checkpoint=RUN["checkpoint_during_learning"],
                                                    task_ids=split("gate"), label="bench").items()}
    probs = p.jev_probs(questions, bench_runs, "bench")
    scores = [score(probs[t], questions, rb["weights"]) + rb["intercept"] for t in bench_runs]
    tau = set_tau(scores, RUN["router"]["escalate_share"])
    save("tau", {"tau": tau, "escalate_share": RUN["router"]["escalate_share"], "test_bench_tasks": len(scores)})
    print(f"tau = {tau:.4f} (frozen before sealed)", flush=True)


# ---------------- stage 5: the sealed exam, once ----------------

def stage_sealed(args) -> None:
    release = ROOT / RUN["sealed"]["release_file"]
    if not release.exists() or not args.release_confirmed:
        sys.exit(f"STOP: the sealed set is held. It runs only after Alexander writes {RUN['sealed']['release_file']} "
                 "and this stage is called with --release-confirmed.")
    p = Phase1()
    sealed = split("sealed")
    final = tuple(load_json("skill_final")["rules"])
    rb, tau = load_json("rubric_final"), load_json("tau")["tau"]  # the original rubric and its cutoff (kept for the record)
    cutoff_file, instr_file = OUT / "jev_cutoff_second_attempt.json", OUT / "verifier_instructions_final.txt"
    if not cutoff_file.exists() or not instr_file.exists():
        sys.exit("STOP: the frozen Jev redesign (instructions and cutoff) is missing; the router cannot be scored.")
    cutoff = json.loads(cutoff_file.read_text())["cutoff"]
    q_final = tuple(Question(**q) for q in rb["questions"])
    q_v0 = tuple(Question(**q) for q in rb["v0"]["questions"])
    one = lambda d: {t: rs[0] for t, rs in d.items()}  # noqa: E731
    # Canonical design (2026-10-09): the checkpoint is on for the final test too. Off runs exist only for question 4.
    v0_on = one(p.run_set(model="minimax", rules=(), checkpoint=True, task_ids=sealed, label="sealed"))
    fin_on = one(p.run_set(model="minimax", rules=final, checkpoint=True, task_ids=sealed, label="sealed"))
    fin_off = one(p.run_set(model="minimax", rules=final, checkpoint=False, task_ids=sealed, label="sealed"))
    gem = one(p.run_set(model="gemini", rules=(), checkpoint=False, task_ids=sealed, label="sealed"))
    as_rec = lambda r: {"credit": r.partial_credit, "cost_usd": r.cost_usd, "seconds": r.model_seconds}  # noqa: E731
    mean = lambda runs: sum(r.partial_credit for r in runs.values()) / len(runs)  # noqa: E731
    results = {}
    # Starting line: starting playbook (checkpoint on) vs Gemini alone
    d1 = [v0_on[t].partial_credit - gem[t].partial_credit for t in sealed]
    results["V2-1_starting_line"] = {"minimax_starting_playbook": mean(v0_on), "gemini": mean(gem),
                                     "diff": sum(d1) / len(d1), "interval_95": list(paired_bootstrap_interval(d1))}
    # Question 2, did MiniMax learn? Final vs starting playbook, both checkpoint on
    d2 = [fin_on[t].partial_credit - v0_on[t].partial_credit for t in sealed]
    nz = [x for x in d2 if x != 0]
    p2 = float(wilcoxon(nz, alternative="greater").pvalue) if nz else 1.0
    results["V2-2a_did_minimax_learn"] = {"starting": mean(v0_on), "final": mean(fin_on), "diff": sum(d2) / len(d2),
                                          "interval_95": list(paired_bootstrap_interval(d2)), "p_one_sided": p2, "learned": p2 < 0.05 and sum(d2) > 0}
    # Question 3, did Jev learn? Both rubrics on the final playbook's checkpoint-on runs
    probs_fin = p.jev_probs(q_final, fin_on, "sealed-on")
    probs_v0q = p.jev_probs(q_v0, fin_on, "sealed-on-starting-rubric")
    good = {t: is_good(fin_on[t].partial_credit) for t in sealed}
    c_fin = [classify(probs_fin[t], q_final, rb["weights"], rb["intercept"]) == good[t] for t in sealed]
    c_v0 = [classify(probs_v0q[t], q_v0, rb["v0"]["weights"], rb["v0"]["intercept"]) == good[t] for t in sealed]
    g = keep_rubric_edit(c_v0, c_fin, p_threshold=0.05)
    results["V2-2b_did_jev_learn"] = {"accuracy_starting_rubric": sum(c_v0) / len(sealed), "accuracy_final_rubric": sum(c_fin) / len(sealed),
                                      "better": g.b, "worse": g.c, "p": g.p_value, "learned": g.keep}
    # Question 1, the main comparison: router (checkpoint on) vs Gemini alone. The router uses the Jev redesign,
    # second attempt, variant 3, and the cutoff frozen on the fresh validation runs (canonical design, Takes).
    sc = verifier_scores(p, fin_on)
    sc_old = {t: score(probs_fin[t], q_final, rb["weights"]) + rb["intercept"] for t in sealed}
    escalate = sorted(t for t in sealed if sc[t] < cutoff)
    fresh = one(p.run_set(model="gemini", rules=(), checkpoint=False, task_ids=escalate, label="sealed-redo", first_attempt=1)) if escalate else {}
    routed = route(sealed, sc, cutoff, {t: as_rec(fin_on[t]) for t in sealed}, {t: as_rec(fresh[t]) for t in fresh},
                   {t: RUN["cost_estimate_per_run"]["jev_call"] for t in sealed})
    results["V2-3_main_comparison"] = v2_3_verdict(routed, {t: as_rec(gem[t]) for t in sealed})
    results["main_comparison"] = "V2-3: router (checkpoint on) vs Gemini alone, sealed exam"
    results["router_jev"] = {"design": "Jev redesign, second attempt, variant 3", "cutoff": cutoff, "escalated": len(escalate),
                             "escalated_share": len(escalate) / len(sealed), "original_rubric_cutoff_unused": tau}
    # How well each Jev separates good from poor final-playbook runs on the sealed exam (same-playbook AUC; one playbook here)
    def jev_quality(scores):
        return evalstats.evaluate([{"task": t, "group": "final", "score": scores[t], "credit": fin_on[t].partial_credit} for t in sealed], boot=1000)
    results["jev_on_sealed"] = {"redesign_second_attempt": jev_quality(sc), "original_rubric": jev_quality(sc_old),
                                "bar": {"auc": 0.65, "auc_ci95_lower_above": 0.5, "gap": 0.10}}
    # MiniMax final alone against Gemini alone, from the same runs (no extra cost)
    dm = [fin_on[t].partial_credit - gem[t].partial_credit for t in sealed]
    results["minimax_final_vs_gemini_alone"] = {"minimax_credit": mean(fin_on), "gemini_credit": mean(gem), "diff": sum(dm) / len(dm),
                                                "interval_95": list(paired_bootstrap_interval(dm)),
                                                "minimax_cost_per_task": sum(r.cost_usd for r in fin_on.values()) / len(sealed),
                                                "gemini_cost_per_task": sum(r.cost_usd for r in gem.values()) / len(sealed)}
    # Question 4, what does the checkpoint add? Final playbook, checkpoint off vs on (an extra)
    read_first = [behaviour(p.tasks[t], fin_on[t].calls, fin_on[t].missed_checks)["read_policy_before_first_write"] for t in sealed]
    results["V2-5_checkpoint_extra"] = checkpoint_verdict(fin_off, fin_on, [x for x in read_first if x is not None])
    results["extra_column_final_playbook_checkpoint_off"] = {"credit": mean(fin_off), "pass_rate": sum(r.passed for r in fin_off.values()) / len(sealed)}
    results["spend_usd"] = p.spend.total_usd
    save("sealed_results", results)
    m = results["V2-3_main_comparison"]
    print(f"main comparison (router, checkpoint on, vs Gemini alone): credit {m['credit']['router']:.3f} vs {m['credit']['gemini']:.3f} "
          f"({m['credit']['diff']:+.3f}; 95% {m['credit']['interval_95'][0]:+.3f} to {m['credit']['interval_95'][1]:+.3f}); "
          f"cost ratio {m['cost_per_task']['ratio']:.2f}; reference lines met: {m['chefs_kiss']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sk = sub.add_parser("skill")
    sk.add_argument("--stop-after-round", type=int, default=None, help="stop once this round's decisions are saved (resumable)")
    sk.set_defaults(fn=stage_skill)
    for name, fn in (("ceiling", stage_ceiling), ("fresh", stage_fresh), ("replay-refused", stage_replay_refused), ("jevdata", stage_jevdata), ("rubric", stage_rubric), ("tau", stage_tau)):
        sub.add_parser(name).set_defaults(fn=fn)
    s = sub.add_parser("sealed")
    s.add_argument("--release-confirmed", action="store_true")
    s.set_defaults(fn=stage_sealed)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
