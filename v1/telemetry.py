"""Live, read-while-running telemetry for a run.

run_status.json  - what each loop is doing right now (stage, set, progress, ETA, spend).
wip_summary.json - everything finished so far: accuracies per evaluation, candidates,
                   gate decisions, current versions. Safe to read at any time; sealed
                   results never appear here until the sealed stage writes them.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, default=str) + "\n")
    temporary.replace(path)


class Telemetry:
    def __init__(self, results_dir: Path, run_id: str, spend=None):
        self.status_path = results_dir / "run_status.json"
        self.summary_path = results_dir / "wip_summary.json"
        self.run_id = run_id
        self.spend = spend
        self.started = time.monotonic()
        self._lock = threading.Lock()
        self._stage_started: dict[str, float] = {}
        self.status: dict[str, Any] = {"run_id": run_id, "started_at": _now(), "loops": {}}
        previous = json.loads(self.summary_path.read_text()) if self.summary_path.exists() else {}
        self.summary: dict[str, Any] = {
            "run_id": run_id,
            "evaluations": previous.get("evaluations", []) if previous.get("run_id") == run_id else [],
            "candidates": previous.get("candidates", []) if previous.get("run_id") == run_id else [],
            "gates": previous.get("gates", []) if previous.get("run_id") == run_id else [],
            "current_versions": previous.get("current_versions", {}) if previous.get("run_id") == run_id else {},
            "notes": previous.get("notes", []) if previous.get("run_id") == run_id else [],
        }

    def _spend(self) -> dict[str, Any]:
        if self.spend is None:
            return {}
        return {"spend_usd": round(self.spend.total_usd, 4), "spend_cap_usd": self.spend.cap_usd,
                "paid_calls": self.spend.calls}

    def stage(self, lane: str, **fields: Any) -> None:
        """Live status for one lane (loop A, loop B, sealed...)."""
        with self._lock:
            key = f"{lane}:{fields.get('stage')}:{fields.get('round')}:{fields.get('set')}:{fields.get('version_id')}"
            self._stage_started.setdefault(key, time.monotonic())
            completed, total = fields.get("completed"), fields.get("total")
            elapsed = time.monotonic() - self._stage_started[key]
            eta = (elapsed / completed * (total - completed)) if completed and total and total >= completed else None
            self.status["loops"][lane] = {
                **fields, "updated_at": _now(),
                "stage_elapsed_seconds": round(elapsed),
                "eta_seconds_for_stage": round(eta) if eta is not None else None,
            }
            self.status.update(updated_at=_now(), elapsed_seconds=round(time.monotonic() - self.started), **self._spend())
            _atomic_write(self.status_path, self.status)
        label = " · ".join(str(fields.get(k)) for k in ("stage", "round", "set", "version_id") if fields.get(k) is not None)
        count = f" {completed}/{total}" if total else ""
        print(f"[{lane}] {label}{count}", flush=True)

    def _write_summary(self) -> None:
        self.summary.update(updated_at=_now(), **self._spend())
        _atomic_write(self.summary_path, self.summary)

    def evaluation(self, *, loop: str, round_number: Any, set_name: str, version_id: str, summary: dict[str, Any]) -> None:
        with self._lock:
            self.summary["evaluations"].append({
                "loop": loop, "round": round_number, "set": set_name, "version_id": version_id,
                **{k: round(v, 4) if isinstance(v, float) else v for k, v in summary.items()},
                "finished_at": _now(),
            })
            self._write_summary()

    def candidate(self, record: dict[str, Any]) -> None:
        with self._lock:
            self.summary["candidates"].append({**record, "at": _now()})
            self._write_summary()

    def gate(self, record: dict[str, Any]) -> None:
        with self._lock:
            self.summary["gates"].append({**record, "at": _now()})
            self._write_summary()

    def current(self, loop: str, version: dict[str, Any]) -> None:
        with self._lock:
            self.summary["current_versions"][loop] = version
            self._write_summary()

    def note(self, text: str) -> None:
        with self._lock:
            self.summary["notes"].append({"at": _now(), "note": text})
            self._write_summary()

    def finish(self, lane: str, **fields: Any) -> None:
        self.stage(lane, stage="done", **fields)
