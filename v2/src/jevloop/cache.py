# Ported from v1/cache.py at tag v1-final (a8aae97); unchanged apart from this line.
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(payload: Any) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, payload: Any) -> dict[str, Any] | None:
        path = self.directory / f"{self.key(payload)}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def put(self, payload: Any, response: dict[str, Any]) -> None:
        path = self.directory / f"{self.key(payload)}.json"
        temporary = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(response, ensure_ascii=False, sort_keys=True))
        temporary.replace(path)

