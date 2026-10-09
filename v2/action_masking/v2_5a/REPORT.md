# V2-5a: the "read the policies first" checkpoint, off vs on (2026-10-08, $5.90)

**Rules:** fixed in `src/jevloop/masking.py` before the run · **Data:** `results.json` · **Script:** `scripts/v2_5a_gate.py`

## The question, plainly

MiniMax tends to act before reading the rulebook. We put a bouncer in the harness: before MiniMax changes any record, it checks whether MiniMax has opened every policy email. If not, the action is held and MiniMax is told which emails to read. Does that make MiniMax break fewer rules, without hurting its work?

## What we did

MiniMax (its starting prompt, temperature 0) did each of the 60 test bench tasks twice: once with the checkpoint off, once with it on. Same tasks, compared one by one. The sealed set was not touched.

## Result: the checkpoint is worth keeping, by the preregistered rule

| On the 60 test bench tasks | Checkpoint off | Checkpoint on | Change (95% range) |
|---|---|---|---|
| **Broken "must not" rules per run** (primary) | 0.88 | **0.67** | **−0.22** (−0.45 to +0.02) |
| Mean credit (guard: must not fall) | 0.57 | **0.65** | **+0.08** (−0.02 to +0.17) |
| Tasks fully passed | 18% | 23% | +5 points |
| Holds per run (guard: at most 2) | — | 0.82 | |
| Cost per run | $0.050 | $0.056 | +12% |
| Steps per run | 18.3 | 21.4 | +17% |
| Wrong and **not** flagged (silent-wrong) | 82% | 42% | |
| Wrong and flagged by the checkpoint (caught-wrong) | 0% | 35% | |

**Verdict:** broken rules fell (primary outcome), credit did not fall, and holds stayed under the limit, so the preregistered rule says **keep the checkpoint**. Both changes point the right way, but both 95% ranges just touch zero: **this is a promising mechanism result, not proof.** A second run per arm would narrow the ranges.

**Sanity check missed its bar:** with the checkpoint on, 75% of runs read every policy email before their first write (bar: 90%). In 7 of the 9 shortfalls, MiniMax **ignored the checkpoint's instruction three times**, hit the 3-hold limit, and was then let through. Sometimes it won't read the rules even when told exactly which emails to read.

## Limits

- One run per arm, and MiniMax varies a lot between runs (a 0.26 average score difference on repeats), so the ranges are wide.
- "Caught-wrong" overstates catching: a flagged run can still be wrong for another reason.
- The policy-email detector is rough (precision 0.50, recall 0.73), so the checkpoint sometimes asks for irrelevant emails and misses some real rules.
- **Fairness (Alexander's observation):** Gemini gets no checkpoint. The headline comparison stays checkpoint off; this result is reported on its own.

**Lines that could be lifted as is:**
- *"With the checkpoint on, MiniMax broke about a quarter fewer rules and scored a little higher, on the same 60 tasks."*
- *"Silent mistakes, wrong and unflagged, fell from 82% of runs to 42%."*
- *"Sometimes the agent ignored the instruction to read the rules three times in a row."*
