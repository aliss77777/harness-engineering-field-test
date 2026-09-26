# Experiment Index

Completed experiments are immutable snapshots. Start a new folder instead of overwriting an earlier run.

| Experiment | Task | Status | Verdict |
|---|---|---|---|
| [`2026-09-26-upworthy-v1`](2026-09-26-upworthy-v1/README.md) | Upworthy headline choice | Complete | Hypothesis weakened |

## Package convention

Each experiment folder contains:

- `README.md` — concise human-readable report.
- `artifacts/` — final versions, controls, evidence, telemetry status, and verdict JSON.
- `config/` — exact `config.yaml` and `task.yaml` used.
- `splits/` — exact practice, gate, and sealed pair IDs.
- `telemetry/` — compressed append-only JSONL event logs.
