# Glossary

One name per concept. Use these exact names in docs, code comments and the UI; no synonyms. Each system gets one colour, the same everywhere (colours to be set in Phase 2).

| Name | Meaning |
|---|---|
| **Agent skill loop** | The agent's learning loop: MiniMax reads its own graded mistakes and edits its own skill file; each edit is gated and kept or rejected (v1's "Loop A" / "LLM loop"). |
| **Jev rubric loop** | The rubric learning loop: weighted yes/no questions about a run, answered by Jev, edited and gated one change at a time (v1's "Loop B", weighted "B+"). |
| **Router** | A cascade: the Cheap agent runs the task once; Jev keeps the run if confident, otherwise the Strong agent does the task. Threshold τ frozen on the gate set (escalates 30% of gate runs). |
| **Strong agent** | Gemini 3.8 Flash (v1's model): the quality bar the Router must match for less. No frontier model. |
| **Cheap agent** | The low-cost, open-weight agent that produces the K candidate runs per task: MiniMax M3 (adopted 2026-10-07). |
| **Editor** | The learning step in both loops: reads the mistakes from a practice round and proposes one edit (to the skill file or the rubric). In v2 it is MiniMax M3; Gemini never edits. |
| **Action masking** | A check before each record-changing action: if the action breaks a policy the agent should have read, it is held (not executed), the agent is told why, and it tries again. Strictly a *shield* (a veto after the action is proposed), not removal from the set of allowed actions. Every hold is logged as a near-miss for the learning loop. |
| **Silent-wrong rate** | Share of runs that were wrong (credit below 1) **and** not flagged by the gate (no hold or flag logged). It overstates catching: a flagged run can still be wrong for another reason. |
| **Sealed set** | Tasks held out from all learning and tuning, scored once at the end. |
| **Learned?** | The final version beats its own starting version on the Sealed set (preregistered test, p < 0.05). |
