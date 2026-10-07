# Jev learning loops

**The question:** can a learned yes/no rubric (answered by Jev), paired with an LLM, learn from real outcomes and match the LLM's quality for less?

This repo holds the series. Each version is a self-contained folder with its own code, data splits, experiments and log.

| Version | What | Status | Start here |
|---|---|---|---|
| **v1** | Six preregistered experiments on public benchmarks (Upworthy headline A/B tests, Chatbot Arena) | Complete | [`v1/RESULTS.md`](v1/RESULTS.md) · [`v1/README.md`](v1/README.md) |
| **v2** | An open-weight agent + Jev vs Gemini 3.8 Flash on back-office business work (Zapier's AutomationBench: Finance, HR) + a Magic Patterns observability UI | Phase 0 (feasibility) in progress | **Tracker: [`v2/README.md`](v2/README.md)** (status, plan, results) · [brief](v2/briefs/Task%20Brief%207_V2_Business.md) |

## v1 in three lines

- **Routing matched the LLM for less.** Jev decides the cases it is confident about and the LLM takes the close calls: **76.2% vs the LLM's 76.3% accuracy at 43% of the cost**, and about a third faster (experiment 5).
- **The rubric learns; the LLM didn't.** The Jev rubric passed its preregistered learning test three times (experiments 2, 3, 6); the LLM loop never did.
- **It learned without an answer key.** Seeing only the click rates of its own choices, the Jev rubric still learned (p 0.02), and the router stayed within the preregistered margin at 46% of the LLM's cost (experiment 6).

Caveats, the scorecard and the learning table: [`v1/RESULTS.md`](v1/RESULTS.md). Side-by-side detail: [`v1/experiments/COMPARISON.md`](v1/experiments/COMPARISON.md). Dated log: [`v1/PLAN.md`](v1/PLAN.md).

## Layout

```
v1/   experiments 1–6: harness code, configs, tests, data splits, archived experiment packages,
      briefs/, PLAN.md, RESULTS.md, ui-demo/ (Magic Patterns demo built from v1's results)
v2/   scaffold for the next project, following its brief (story, glossary, experiment template)
```

Each version runs from inside its own folder (for v1: `cd v1`, then the commands in [`v1/README.md`](v1/README.md)). The repo as it stood before this split is tagged `v1-final`; experiment 1's code is also at tag `exp1-upworthy-v1`.
