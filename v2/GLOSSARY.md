# Glossary

> **The canonical words are in the table "The words we use" in [`briefs/V2 Phase 1 Canonical Experiment Design.md`](briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md)** (2026-10-09). It outranks this page.

One name per concept. Use these exact names in docs, code comments and the UI; no synonyms. Each system gets one colour, the same everywhere (colours to be set in Phase 2).

| Name | Meaning |
|---|---|
| **Agent skill loop** | The agent's learning loop: MiniMax reads its own graded mistakes and edits its own skill file; each edit goes through the keep-or-reject test (v1's "Loop A" / "LLM loop"). |
| **Jev rubric loop** | The rubric learning loop: weighted yes/no questions about a run, answered by Jev, edited one change at a time, each change through the keep-or-reject test (v1's "Loop B", weighted "B+"). |
| **Router** | A cascade: the Cheap agent runs the task once; Jev keeps the run if confident, otherwise the Strong agent does the task. Threshold τ frozen on the test bench (escalates 30% of test bench runs). |
| **Strong agent** | Gemini 3.8 Flash (v1's model): the quality bar the Router must match for less. No frontier model. |
| **Cheap agent** | The low-cost, open-weight agent that produces the K candidate runs per task: MiniMax M3 (adopted 2026-10-07). |
| **Editor** | The learning step in both loops: reads the mistakes from a practice round and proposes one edit (to the skill file or the rubric). In v2 it is MiniMax M3; Gemini never edits. |
| **Action masking** | A check before each record-changing action: if the action breaks a policy the agent should have read, it is held (not executed), the agent is told why, and it tries again. Strictly a *shield* (a veto after the action is proposed), not removal from the set of allowed actions. Every hold is logged as a near-miss for the learning loop. |
| **Silent-wrong rate** | Share of runs that were wrong (credit below 1) **and** not flagged by the checkpoint (no hold or flag logged). It overstates catching: a flagged run can still be wrong for another reason. |
| **Checkpoint** | The action-masking check built into the harness: before the agent changes any record, it confirms the agent has read every policy email; if not, the action is held and the agent is told which emails to read. (Formerly "the gate"; renamed 2026-10-08.) |
| **Test bench** | The 60 held-out tasks used to try each proposed fix before keeping it (file: `phase1/splits/gate.txt`). The other sets are practice (60) and sealed (80). (Formerly "the gate set"; renamed 2026-10-08.) |
| **Keep-or-reject test** | The rule that decides whether a proposed fix is kept, by comparing it with the current version on the test bench. (Formerly "the gate"; renamed 2026-10-08.) |
| **Take 1 / Take 2** | An attempt at Phase 1 (not "run": a run is one task execution). Take 1: 2026-10-09, p-value keep test, stopped after round 2, nothing kept. Take 2: 2026-10-10, margin keep test. |
| **P-value keep test** | Take 1's playbook test: targeted failure kind clearly drops (p < 0.10) and overall credit does not fall. |
| **Margin keep test** | Take 2's playbook test: targeted failure kind improves, overall credit up by at least 0.02, fully passed tasks not lower; no p-value. |
| **Jev refit** | Re-estimating how much each rubric question counts, on about 1,050 labelled runs, tested on tasks held out of fitting. |
| **Jev redesign, first / second attempt** | Jev as a checker that sees the source data, policy emails and the agent's writes, with questions written per task. Second attempt adds variants 1 to 4 (more question sets, a compliance set, a per-write check), chosen on development tasks and tested once on fresh runs. |
| **AUC** | Of all good-run / poor-run pairs, the share where the good run scored higher; 0.5 is chance, 1.0 perfect. |
| **Same-playbook comparison** | AUC computed only between runs made with the same playbook version. |
| **Sealed set** | Tasks held out from all learning and tuning, scored once at the end. |
| **Learned?** | The final version beats its own starting version on the Sealed set (preregistered test, p < 0.05). |
