"""Experiment 5: route between Jev (J*) and the LLM (A*).

Jev scores every pair. If its absolute score margin is at least tau, Jev's pick is final;
otherwise the LLM decides (falling back to Jev if Gemini refuses the pair). tau is the
gate-set margin quantile that sends a fixed share of pairs to the LLM.
"""
from __future__ import annotations

from typing import Any


def tau_for_share(gate_margins: list[float], llm_share: float) -> float:
    """Smallest tau with at most llm_share of gate pairs below it (sent to the LLM)."""
    ordered = sorted(gate_margins)
    k = int(llm_share * len(ordered))  # pairs strictly below tau go to the LLM
    return ordered[k] if k < len(ordered) else float("inf")


def route(margins: list[float], jev_records: list[dict[str, Any]], llm_records: list[dict[str, Any]],
          tau: float) -> list[dict[str, Any]]:
    out = []
    for margin, j, a in zip(margins, jev_records, llm_records):
        if j["pair_id"] != a["pair_id"]:
            raise ValueError("LLM and Jev records must be aligned")
        to_llm = margin < tau
        use_llm = to_llm and not a.get("blocked")
        pick = a["prediction"] if use_llm else j["prediction"]
        out.append({
            "pair_id": j["pair_id"], "winner": j["winner"], "prediction": pick,
            "correct": pick == j["winner"], "routed_to_llm": to_llm, "decided_by": "llm" if use_llm else "jev",
            "cost": float(j.get("cost", 0)) + (float(a.get("cost", 0)) if to_llm else 0.0),
            "latency_ms": float(j.get("latency_ms", 0)) + (float(a.get("latency_ms", 0)) if to_llm else 0.0),
        })
    return out
