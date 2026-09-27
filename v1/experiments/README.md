# Experiment Index

Completed experiments are immutable snapshots. Start a new folder instead of overwriting an earlier run.

| Experiment | Task | Status | Verdict |
|---|---|---|---|
| [`2026-09-26-upworthy-v1`](2026-09-26-upworthy-v1/README.md) | Upworthy headline choice | Complete | Hypothesis weakened |
| [`2026-09-26-arena-v1`](2026-09-26-arena-v1/README.md) | Chatbot Arena, long responses | Complete | Only the Jev loop learned |
| [`2026-09-26-arena-trace-v1`](2026-09-26-arena-trace-v1/README.md) | Arena, decision-trace Jev loop | Complete | Trace: no detectable difference · weights: help |

Cross-experiment summary: [`COMPARISON.md`](COMPARISON.md).

## Package convention

Each experiment folder contains:

- `README.md` — concise human-readable report.
- `artifacts/` — final versions, controls, evidence, telemetry status, and verdict JSON.
- `config/` — exact `config.yaml` and `task.yaml` used.
- `splits/` — exact practice, gate, and sealed pair IDs.
- `telemetry/` — compressed append-only JSONL event logs.
