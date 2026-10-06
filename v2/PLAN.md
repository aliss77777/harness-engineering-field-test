# v2 plan and log

Dated log of every decision, deviation and fix (same discipline as [`../v1/PLAN.md`](../v1/PLAN.md)). Design: [`briefs/Task Brief 7_V2_Business.md`](briefs/Task%20Brief%207_V2_Business.md).

## Log

- 2026-10-05: **Repo restructured** into `v1/` (experiments 1–6, unchanged and still runnable from `v1/`) and `v2/` (this scaffold). Prior state tagged `v1-final`. **Decision (Alexander):** v2 lives as a folder in this repo rather than the new `jev-loop-v2` repo the brief recommended (brief section 9, decision 1). Scaffold follows brief section 4; no experiments, code or paid calls yet.

- 2026-10-05: **AutomationBench in place (free checks only).** Alexander downloaded v1.0.6 to `z-ignore/` (git-ignored). Licence is MIT. Installed into `v2/.venv` (Python 3.13, pip; no `uv`). Bench tests 1,398 passed with keys unset; all 800 tasks load and grade; a do-nothing run scores 0 everywhere. Details: `phase0/FEASIBILITY.md`. **Not yet (Alexander):** the paid Phase 0 spike and the model choice.

## Open decisions (brief section 9)

- [x] Repo: folder in this repo (2026-10-05).
- [ ] Domains (suggested: Support + Sales), informed by Phase 0.
- [ ] Models: Cheap agent, Strong agent, escalation option (LLM judge vs Strong agent re-run).
- [ ] Budget cap after Phase 0 (placeholder $60, enforced in code).
[line omitted from the public copy]
- [x] AutomationBench licence: MIT (2026-10-05).
