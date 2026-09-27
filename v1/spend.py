from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class SpendCapExceeded(RuntimeError):
    """Paid spend reached the configured cap; the run must stop."""


class SpendTracker:
    """Running total of real (uncached) API spend, persisted across processes.

    Cache replays are not added: they cost nothing now, although results still
    charge them at the original call's cost.
    """

    def __init__(self, path: Path, cap_usd: float, flush_seconds: float = 2.0):
        self.path = path
        self.cap_usd = float(cap_usd)
        self.flush_seconds = flush_seconds
        self._lock = threading.Lock()
        self._last_flush = 0.0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stored = json.loads(path.read_text()) if path.exists() else {}
        self.total_usd = float(stored.get("total_usd", 0.0))
        self.calls = int(stored.get("calls", 0))

    def check(self) -> None:
        if self.total_usd >= self.cap_usd:
            self.flush()
            raise SpendCapExceeded(
                f"spend ${self.total_usd:.4f} reached cap ${self.cap_usd:.2f}"
            )

    def record(self, cost_usd: float) -> None:
        with self._lock:
            self.total_usd += float(cost_usd or 0.0)
            self.calls += 1
            due = time.monotonic() - self._last_flush >= self.flush_seconds
        if due:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            record = {"total_usd": self.total_usd, "calls": self.calls, "cap_usd": self.cap_usd}
            self._last_flush = time.monotonic()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, indent=2) + "\n")
            temporary.replace(self.path)
