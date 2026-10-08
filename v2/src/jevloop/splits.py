"""Phase 1 task split (briefs/Phase 1 design.md): practice 60, gate 60, sealed 80, stratified by domain.

Tasks used in Phase 0 (they informed model choice) go into practice or gate, never sealed.
"""
from __future__ import annotations

import random


def _num(task_id: str) -> int:
    return int(task_id.split(":")[1])


def phase1_split(
    task_ids_by_domain: dict[str, list[str]],
    phase0_ids: set[str],
    *,
    seed: int,
    practice: int = 30,
    gate: int = 30,
    sealed: int = 40,
) -> dict[str, list[str]]:
    """Per domain: `sealed` tasks drawn only from tasks Phase 0 never touched; the rest split into
    practice and gate. Returns {"practice": [...], "gate": [...], "sealed": [...]} in a stable order."""
    out: dict[str, list[str]] = {"practice": [], "gate": [], "sealed": []}
    for domain in sorted(task_ids_by_domain):
        ids = sorted(task_ids_by_domain[domain], key=_num)
        if len(ids) != practice + gate + sealed:
            raise ValueError(f"{domain}: expected {practice + gate + sealed} tasks, got {len(ids)}")
        rng = random.Random(f"{seed}:{domain}")
        fresh = [t for t in ids if t not in phase0_ids]
        rng.shuffle(fresh)
        if len(fresh) < sealed:
            raise ValueError(f"{domain}: only {len(fresh)} tasks unused in Phase 0, need {sealed} for sealed")
        out["sealed"] += fresh[:sealed]
        rest = [t for t in ids if t not in set(fresh[:sealed])]
        rng.shuffle(rest)
        out["practice"] += rest[:practice]
        out["gate"] += rest[practice:]
    return {k: sorted(v, key=lambda t: (t.split(":")[0], _num(t))) for k, v in out.items()}
