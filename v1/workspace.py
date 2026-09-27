from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parent

DEFAULT_PATHS = {"pairs": "data/pairs", "splits": "data/splits", "results": "results", "logs": "logs"}


@dataclass(frozen=True)
class Workspace:
    """One task's config, wording and output locations (MVP brief 7.1: the task is a config)."""

    root: Path
    config: dict[str, Any]
    task: dict[str, Any]

    @classmethod
    def load(cls, config_path: str = "config.yaml", task_path: str = "task.yaml") -> "Workspace":
        config = yaml.safe_load((ROOT / config_path).read_text())
        task = yaml.safe_load((ROOT / task_path).read_text())
        return cls(ROOT, config, task)

    def path(self, kind: str) -> Path:
        relative = {**DEFAULT_PATHS, **self.task.get("paths", {})}[kind]
        directory = self.root / relative
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def columns(self) -> dict[str, str | None]:
        return {"context": None, "x": "headline_x", "y": "headline_y", **self.task.get("columns", {})}

    @property
    def labels(self) -> dict[str, str]:
        return {"x": "X", "y": "Y", **self.task.get("labels", {})}

    @property
    def wording(self) -> dict[str, str]:
        return self.task["wording"]

    def pair_view(self, row: Any) -> dict[str, str]:
        """Only the text a decider may see: no outcome, no model names."""
        columns = self.columns
        return {
            "pair_id": str(row["pair_id"]),
            "context": "" if not columns["context"] else str(row[columns["context"]]),
            "x": str(row[columns["x"]]),
            "y": str(row[columns["y"]]),
        }

    def jev_state(self, context: str, item: str) -> str:
        template = self.task.get("jev_state_template", "{item}")
        return template.format(context=context, item=item)


def read_pairs(path: Path) -> pd.DataFrame:
    """Read a pair file with text kept as text: a response that is literally "N/A" or
    "null" must not become a missing value (pandas' default)."""
    return pd.read_csv(path, dtype={"pair_id": str}, keep_default_na=False, na_values=[])
