from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunProgress:
    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self.started = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def update(self, **fields: Any) -> None:
        completed = int(fields.get("completed", 0) or 0)
        total = int(fields.get("total", 0) or 0)
        elapsed = time.monotonic() - self.started
        eta_seconds = (elapsed / completed * (total - completed)) if completed and total >= completed else None
        record = {
            "run_id": self.run_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed),
            "eta_seconds_for_current_stage": round(eta_seconds) if eta_seconds is not None else None,
            **fields,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(self.path)
        label = " · ".join(str(record.get(key)) for key in ("loop", "round", "set") if record.get(key) is not None)
        count = f"{completed}/{total}" if total else ""
        print(f"[{record.get('stage', 'running')}] {label} {count}", flush=True)
