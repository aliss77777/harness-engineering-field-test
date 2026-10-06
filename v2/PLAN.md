# v2 plan and log

Dated log of every decision, deviation and fix (same discipline as [`../v1/PLAN.md`](../v1/PLAN.md)). Design: [`briefs/Task Brief 7_V2_Business.md`](briefs/Task%20Brief%207_V2_Business.md).

## Log

- 2026-10-05: **Repo restructured** into `v1/` (experiments 1–6, unchanged and still runnable from `v1/`) and `v2/` (this scaffold). Prior state tagged `v1-final`. **Decision (Alexander):** v2 lives as a folder in this repo rather than the new `jev-loop-v2` repo the brief recommended (brief section 9, decision 1). Scaffold follows brief section 4; no experiments, code or paid calls yet.

- 2026-10-05: **AutomationBench in place (free checks only).** Alexander downloaded v1.0.6 to `z-ignore/` (git-ignored). Licence is MIT. Installed into `v2/.venv` (Python 3.13, pip; no `uv`). Bench tests 1,398 passed with keys unset; all 800 tasks load and grade; a do-nothing run scores 0 everywhere. Details: `phase0/FEASIBILITY.md`. **Not yet (Alexander):** the paid Phase 0 spike and the model choice.

- 2026-10-05: **Free Phase 0 harness built (no model calls).** `src/jevloop/`: `cache`, `spend`, `log`, `gate` ported unchanged from v1 at `v1-final` (each file names its source); `bench` (the only AutomationBench import; grading checks stay on a private field agents never receive), `runs` (K candidate runs per task, fresh world each, ordered output independent of concurrency), `summary` (trigger + tool calls + state diff, the Jev rubric's input), `feasibility` (V2-1 frame: first run, random pick, oracle best-of-K, mixed share; brief's go/no-go rule), `agents` (do-nothing and scripted only). Scripts: `phase0_free_check.py`, `export_ui_data.py` (writes `ui-data/` from `story/insights.yaml` and experiment front matter). Tests: 27 passed. Brief item 3d answered: yes, our own loop drives the bench. **Not ported yet:** v1's OpenRouter client; the agent needs a tool-calling client, built after the model choice. **No shared `harness/` package:** v1 stays frozen; reconsider after Phase 1.
- 2026-10-05: **Phase 2 floor set (Alexander).** A revised Magic Patterns prompt produced a much better demo, kept locally at `z-ignore/v2-massive-improvement/` (not committed). It is the minimum bar for the Phase 2 UI. What it does well: one scrolling story in chapters (Hero → Setup → Experiment 3's learning → Router → Takeaways) with chapter navigation, the router's mechanism shown (confident vs close-call split, accuracy-vs-LLM-share curve, equivalence interval), and a kept-edit diff and edit funnel for learning. Spot-checked against `v1/RESULTS.md`: router 76.2% vs LLM 76.3%, $0.633 vs $1.481 per 1k (43%), 874 vs 1,285 ms, confident cases 81.6% vs 81.7%, 36 vs 37 head-to-head, interval −1.8 to +1.6, all match. What v2 must add: numbers come from `ui-data/*.json` (that demo still hardcodes them in `src/data/*.ts`), and insight sentences come verbatim from `story/insights.yaml`.

## Open decisions (brief section 9)

- [x] Repo: folder in this repo (2026-10-05).
- [ ] Domains (suggested: Support + Sales), informed by Phase 0.
- [ ] Models: Cheap agent (**decided by the Phase 0 bake-off**: Gemini 3.8 Flash vs Nemotron 3 Super vs gpt-oss-120b), Strong agent, escalation option (LLM judge vs Strong agent re-run).
- [ ] Budget cap after Phase 0 (placeholder $60, enforced in code).
[line omitted from the public copy]
- [x] AutomationBench licence: MIT (2026-10-05).
- 2026-10-05: **Cheap-agent bake-off added to Phase 0 (Alexander).** Open-weight models on OpenRouter are much cheaper than Gemini 3.8 Flash ($0.75 / $3.75 per million tokens): Nemotron 3 Super $0.08 / $0.45 (≈ 8–9× cheaper), gpt-oss-120b $0.037 / $0.17 (≈ 20×). Same 20 tasks, one run each, $5 cap; selection rule fixed in advance: the cheapest model with a 20–80% pass rate and under 10% tool-call errors, else keep Gemini. One provider pinned per model. The editor stays on a strong model. If an open-weight model wins, the lean Phase 1 estimate drops from ≈ $40–60 to ≈ $20–30. Details: `phase0/FEASIBILITY.md`.
