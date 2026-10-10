# Sealed exam release note

Released by Alexander Liss, in chat, 2026-10-10 at 18:24 UTC. His words: "love it! write that up in the README ... then let's start the sealed exam".

Conditions recorded at release (pre-flight, 2026-10-10):

- Final playbook `s78766c8a` (rules R1a and R2x); starting playbook `v0` (no rules); checkpoint on for both, and for the final playbook once more with it off (question 4).
- Router: Jev redesign, second attempt, variant 3; instructions `phase1/run/take2/verifier_instructions_final.txt`; cutoff 0.7563 (frozen on 120 fresh test bench runs). Original rubric and cutoff kept only for the record.
- Gemini: no playbook, no checkpoint, one run per task; escalated tasks get a fresh Gemini run.
- One run per task, 80 sealed tasks, opened once. Spend cap $130; tracker at $75.35.
- Nothing is tuned on the sealed set afterwards.
