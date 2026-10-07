# Glossary

One name per concept. Use these exact names in docs, code comments and the UI; no synonyms. Each system gets one colour, the same everywhere (colours to be set in Phase 2).

| Name | Meaning |
|---|---|
| **Agent skill loop** | The LLM learning loop: the agent's skill/instruction file is edited, gated and kept or rejected (v1's "Loop A" / "LLM loop"). |
| **Jev rubric loop** | The rubric learning loop: weighted yes/no questions about a run, answered by Jev, edited and gated one change at a time (v1's "Loop B", weighted "B+"). |
| **Router** | Jev keeps the runs it is confident about; the rest escalate to an LLM judge or the Strong agent. Threshold τ frozen on the gate set. |
| **Strong agent** | Gemini 3.8 Flash (v1's model): the quality bar the Router must match for less. No frontier model. |
| **Cheap agent** | The low-cost, open-weight agent that produces the K candidate runs per task: Nemotron 3 Super, if the comparability check passes. |
| **Sealed set** | Tasks held out from all learning and tuning, scored once at the end. |
| **Learned?** | The final version beats its own starting version on the Sealed set (preregistered test, p < 0.05). |
