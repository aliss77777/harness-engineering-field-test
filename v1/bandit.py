"""Experiment 6 core: pick-one-of-K policies, partial feedback, and bandit metrics.

A test is {test_id, headlines, ctr, ...}. A policy returns one index per test. The only
outcome a learner may see is ctr[chosen]. Everything that uses the other headlines'
outcomes (lift, regret, hit rate) is evaluation-only and never reaches an editor.
"""
from __future__ import annotations

import hashlib
import random
import re
from concurrent.futures import as_completed
from typing import Any, Callable

import numpy as np

from deciders import RubricQuestion, rubric_score
from evaluation import failfast_pool
from openrouter_llm import ContentBlockedError

USAGE_KEYS = ("input_tokens", "output_tokens", "reasoning_tokens", "cost", "latency_ms")


# ---------- evaluation-only metrics (use every headline's outcome) ----------

def lift(test: dict, index: int) -> float:
    """Click lift of the chosen headline over a random pick, in points (random = 0)."""
    mean = float(np.mean(test["ctr"]))
    return 100.0 * (test["ctr"][index] / mean - 1.0) if mean > 0 else 0.0


def regret(test: dict, index: int) -> float:
    best = max(test["ctr"])
    return (best - test["ctr"][index]) / best if best > 0 else 0.0


def hit(test: dict, index: int) -> bool:
    return test["ctr"][index] == max(test["ctr"])


# ---------- deciders ----------

class LLMPicker:
    """The LLM sees a batch of tests, each with numbered headlines, and picks one per test."""

    def __init__(self, client, wording: dict[str, str]):
        self.client = client
        self.wording = wording

    def pick_batch(self, instructions: str, tests: list[dict], event: dict) -> tuple[dict[str, tuple[int, str]], dict]:
        rendered = "\n\n".join(
            f"=== Test {t['test_id']} ===\n" + "\n".join(f"{i + 1}. {h}" for i, h in enumerate(t["headlines"]))
            for t in tests)
        prompt = f"""Use these instructions to predict {self.wording['outcome']} in each test.

INSTRUCTIONS:
{instructions}

TESTS (each lists the headlines tested for one story):
{rendered}

For every test: {self.wording['decider_question']} Answer with the headline's number, then one short, single-line reason. Do not omit tests."""
        schema = {"type": "object", "properties": {"decisions": {"type": "array", "items": {
            "type": "object", "properties": {"test_id": {"type": "string"}, "pick": {"type": "integer"},
                                             "reason": {"type": "string"}},
            "required": ["test_id", "pick", "reason"], "additionalProperties": False}}},
            "required": ["decisions"], "additionalProperties": False}
        self.client.last_call = {}
        result = self.client.generate_json(prompt=prompt, schema=schema,
                                           event={**event, "pair_id": [t["test_id"] for t in tests]})
        usage = dict(self.client.last_call)
        by_id = {t["test_id"]: t for t in tests}
        out: dict[str, tuple[int, str]] = {}
        for item in result.get("decisions", []):
            test_id = str(item["test_id"])
            if test_id not in by_id or test_id in out:
                raise ValueError(f"unexpected or duplicate test {test_id}")
            pick = int(item["pick"]) - 1
            if not 0 <= pick < len(by_id[test_id]["headlines"]):
                raise ValueError(f"pick out of range for test {test_id}")
            out[test_id] = (pick, " ".join(str(item["reason"]).split()))
        if set(out) != set(by_id):
            raise ValueError(f"decisions do not cover the batch: missing {sorted(set(by_id) - set(out))}")
        return out, usage


def llm_picks(picker: LLMPicker, instructions: str, tests: list[dict], *, batch_size: int, workers: int,
              seed: int, event: dict, progress: Callable | None = None) -> dict[str, dict]:
    """LLM picks for every test (cached per batch). Refused tests get a seeded random pick, flagged."""
    batches = [tests[i:i + batch_size] for i in range(0, len(tests), batch_size)]

    def run(number: int, batch: list[dict]):
        try:
            picks, usage = picker.pick_batch(instructions, batch, {**event, "batch": number})
            return {tid: {"pick": p, "reason": r, "blocked": False,
                          **{k: usage.get(k, 0) / len(batch) for k in USAGE_KEYS}} for tid, (p, r) in picks.items()}
        except (ValueError, ContentBlockedError):
            out = {}
            for test in batch:  # one test at a time
                try:
                    picks, usage = picker.pick_batch(instructions, [test], {**event, "batch": number, "single": True})
                    p, r = picks[test["test_id"]]
                    out[test["test_id"]] = {"pick": p, "reason": r, "blocked": False,
                                            **{k: usage.get(k, 0) for k in USAGE_KEYS}}
                except ContentBlockedError:
                    coin = random.Random(f"{seed}:blocked:{test['test_id']}").randrange(len(test["headlines"]))
                    out[test["test_id"]] = {"pick": coin, "reason": None, "blocked": True, **{k: 0 for k in USAGE_KEYS}}
            return out

    results: dict[str, dict] = {}
    with failfast_pool(workers) as pool:
        futures = [pool.submit(run, n, b) for n, b in enumerate(batches)]
        for future in as_completed(futures):
            results.update(future.result())
            if progress:
                progress(completed=len(results), total=len(tests))
    return results


def jev_scores(client, questions_data: list[dict], weights: dict[str, float] | None, tests: list[dict], *,
               workers: int, event: dict, state: Callable[[str], str] = lambda h: h,
               progress: Callable | None = None) -> dict[str, dict]:
    """Jev answers the rubric for every headline; returns per-test scores, probabilities and cost."""
    questions = [RubricQuestion(**q) for q in questions_data]

    def run(test: dict):
        probs, cost, latency = [], 0.0, 0.0
        for index, headline in enumerate(test["headlines"]):
            p = client.evaluate(state(headline), questions,
                                {**event, "pair_id": test["test_id"], "item_side": str(index)})
            usage = dict(client.last_call)
            cost += float(usage.get("cost", 0) or 0)
            latency += float(usage.get("latency_ms", 0) or 0)
            probs.append(p)
        scores = [rubric_score(questions, p, weights) for p in probs]
        return test["test_id"], {"scores": scores, "probs": probs, "cost": cost, "latency_ms": latency}

    out: dict[str, dict] = {}
    with failfast_pool(workers) as pool:
        futures = [pool.submit(run, t) for t in tests]
        for future in as_completed(futures):
            test_id, value = future.result()
            out[test_id] = value
            if progress and (len(out) % 50 == 0 or len(out) == len(tests)):
                progress(completed=len(out), total=len(tests))
    return out


def jev_pick(test: dict, scored: dict, seed: int) -> tuple[int, float]:
    """Top-scoring headline (seeded tie-break) and the margin to the runner-up."""
    scores = scored["scores"]
    top = max(scores)
    tied = [i for i, s in enumerate(scores) if s == top]
    pick = tied[0] if len(tied) == 1 else random.Random(f"{seed}:tie:{test['test_id']}").choice(tied)
    ordered = sorted(scores, reverse=True)
    return pick, ordered[0] - ordered[1]


def router_tau(margins: list[float], llm_share: float) -> float:
    """Label-free: the margin quantile that sends llm_share of these tests to the LLM."""
    ordered = sorted(margins)
    k = int(llm_share * len(ordered))
    return ordered[k] if k < len(ordered) else float("inf")


# ---------- exploration ----------

def explore(test: dict, greedy: int, *, rate: float, seed: int, round_number: int) -> tuple[int, bool]:
    """With probability `rate` (seeded per test and round), pick a different headline at random."""
    rng = random.Random(f"{seed}:explore:{round_number}:{test['test_id']}")
    if rng.random() >= rate:
        return greedy, False
    others = [i for i in range(len(test["headlines"])) if i != greedy]
    return rng.choice(others), True


# ---------- the only outcome a learner may see ----------

def observe(test: dict, index: int) -> dict[str, Any]:
    """The chosen headline's click rate and impressions. Nothing about the other headlines."""
    return {"ctr": test["ctr"][index], "impressions": test["impressions"][index]}


def bandit_evidence(decisions: list[dict], questions_data: list[dict]) -> list[dict]:
    """Per rubric question: mean observed click rate of chosen headlines where Jev said yes vs no.
    Built only from chosen headlines and their observed rewards."""
    rows = []
    for q in questions_data:
        qid = q["question_id"]
        yes = [d["observed"]["ctr"] for d in decisions if d["chosen_probs"][qid] >= 0.5]
        no = [d["observed"]["ctr"] for d in decisions if d["chosen_probs"][qid] < 0.5]
        rows.append({"question_id": qid, "direction": q["direction"],
                     "chosen_yes": len(yes), "mean_click_rate_when_yes": round(100 * np.mean(yes), 3) if yes else None,
                     "chosen_no": len(no), "mean_click_rate_when_no": round(100 * np.mean(no), 3) if no else None})
    return rows


# ---------- policy C: Thompson sampling on surface features ----------

SURFACE = ("length", "question_mark", "number", "you", "i_or_me", "exclamation_mark")


def surface_features(headline: str) -> np.ndarray:
    lowered = headline.lower()
    return np.array([len(headline) / 100, float("?" in headline), float(bool(re.search(r"\d", headline))),
                     float(bool(re.search(r"\byou\b", lowered))), float(bool(re.search(r"\b(i|me)\b", lowered))),
                     float("!" in headline), 1.0])


class ThompsonPolicy:
    """Bayesian linear regression on surface features predicting the chosen headline's click
    rate (in % points, centred per update batch). Learns only from chosen headlines."""

    def __init__(self, prior_variance: float, noise_variance: float, seed: int):
        d = len(SURFACE) + 1
        self.precision = np.eye(d) / prior_variance
        self.b = np.zeros(d)
        self.noise = noise_variance
        self.seed = seed

    def mean(self) -> np.ndarray:
        return np.linalg.solve(self.precision, self.b)

    def pick(self, test: dict, *, sample: bool, round_number: int) -> int:
        weights = self.mean()
        if sample:
            key = hashlib.sha256(f"{self.seed}:{round_number}:{test['test_id']}".encode()).hexdigest()
            rng = np.random.default_rng(int(key[:8], 16))
            weights = rng.multivariate_normal(weights, np.linalg.inv(self.precision))
        scores = [float(surface_features(h) @ weights) for h in test["headlines"]]
        return int(np.argmax(scores))

    def update(self, observations: list[tuple[str, float]]) -> None:
        if not observations:
            return
        centre = float(np.mean([100 * ctr for _, ctr in observations]))
        for headline, ctr in observations:
            x = surface_features(headline)
            self.precision += np.outer(x, x) / self.noise
            self.b += x * (100 * ctr - centre) / self.noise
