# MVP brief: does Jev make a self-learning loop better?

**Written:** 2026-09-25 · **Revised:** 2026-09-26 (v2: learning step made central and fully specified; fair starting versions; same-image data filter; statistical verdict rules; task as config. v2.1: Loop A gives a one-line reason per pick and learns from those reasons. v2.2: parked the contextual bandit idea in 11.1. v2.3: standalone repo; code baseline also scored on the sealed set and clarified as a warning, not a verdict. v2.4: Section 1 is now the executive summary: the claim, its limits, pre-registered headlines and the story arc. v2.5: Loop B scores by summing Jev probabilities to avoid ties; memorization risk called out in 7.4; how-to-build callout at the top of Section 9\) · **Owner:** Alexander **Replaces:** the v4 brief as the working plan. v4 is kept as the parking lot (`BRIEF-v4-parking-lot.md`). None of it is in scope today. **Time budget:** 4 hours to build and run, 4 hours to polish. One day. **Task shape for the coding agent:** build directly after a 15-minute preflight (Section 9.4), in a **new standalone repo**. No investigate-and-recommend phase.

---

## 1\. Executive summary

### 1.1 What v1 tests

Whether a decision model (Jev) helps an AI agent learn its own decision criteria from real outcomes, better or more cheaply than an LLM that learns from its own reasoning. One decision step, one dataset (Upworthy A/B tests), one day. Everything else is parked until this result exists: **test one hypothesis in one day, then decide whether to scale.**

### 1.2 The claim v1 can support, if it works

> "On a decision with real outcomes, a loop that learned its criteria through Jev matched (or beat) an LLM loop that learned from its own reasoning, at a fraction of the cost per decision."

**Limits on that claim:**

- **One decision step, not a whole workflow.** Say "a decision step inside an agent," not "an agentic workflow."  
- **Savings are per decision, not for the learning itself.** Both loops use an LLM editor, so learning costs are similar. Report both numbers (Section 10).  
- **"Jev" only after Loop C.** Without it, the honest claim is "rubric-based learning" (Section 6).  
- **One dataset.** Generality comes later (story arc, act 4).

**Why it's more than task completion:** the loop learns *which criteria predict success*, and those criteria are readable. That answers a practical question: people can edit a rubric by hand, but how do you know an edit made things better?

### 1.3 Pre-registered headlines

Drafted before running, so the story is fixed along with the numbers. After the run, use the sentence matching the verdict in Section 8 and fill in the numbers. Nothing else.

| Verdict (Section 8\) | Headline sentence |
| :---- | :---- |
| **Jev loop learns better** | "Given real A/B test outcomes, an agent that learned its criteria through a decision model picked X% of winners on tests it had never seen, beating an LLM that learned from its own reasoning (Y%), at Z times lower cost per decision." |
| **Learns as well, far cheaper** | "An agent that learned its criteria through a decision model matched an LLM that learned from its own reasoning (X% vs Y% on unseen tests), at Z times lower cost per decision." |
| **Hypothesis weakened** | "On real A/B test outcomes, an LLM learning from its own reasoning beat a decision-model rubric (X% vs Y%). Here's why structured feedback wasn't enough." |
| **No signal** | "Neither approach could predict which headline won (both near 50%). Headline wording alone didn't carry enough signal, and here's what that means for testing whether agents learn." |
| **Inconclusive** | "Early signs, not proof: X% vs Y% on 500 unseen tests is too close to call. Here's the bigger test." |

**Wording rules:**

- Write "a decision model" or "Jev" only if Loop C shows Jev specifically helps. Otherwise write "a yes/no rubric."  
- Write "learned" only if the learning check passed (final version beats version 0). Otherwise describe what it started with, not what it learned.  
- Always name the scope: one decision task, 2013 to 2015 Upworthy data.

### 1.4 The story arc (future experiments)

| Act | Question | Where it lives | What it needs |
| :---- | :---- | :---- | :---- |
| **1** | Can a decision model help an agent learn its criteria cheaply? | This MVP | Nothing more |
| **2** | Do the learned criteria make generated output better than a naive LLM's? | Rung 4 (writer) | A scoring plan: new headlines have no click data. Either a calibrated judge, or real traffic ("the rubric screens candidates; the survivors go into a real A/B test") |
| **3** | Can it learn when it only sees results for what it shipped? | 11.1 (contextual bandit) | Tests with 3+ variants. The value is **realism** (real businesses only see results for what they ship), not better generalization |
| **4** | Does it hold on a different business task? | Rung 3 (second task) | A new `task.yaml`. This is where generalization is shown |

The honest gate (rung 2\) can run as a thread through all four acts: every learned change is only kept if it survives a Stats Engine-style test.

---

## 2\. What "learning" means here

Tom Mitchell's definition (*Machine Learning*, 1997): a program learns from experience **E** with respect to a task **T** and performance measure **P** if its performance at T, as measured by P, improves with E.

|  | In this experiment |
| :---- | :---- |
| **T** (task) | Given two real headlines from the same A/B test, pick the one more readers clicked |
| **P** (performance) | Accuracy on sealed pairs neither loop ever saw |
| **E** (experience) | Rounds of results on practice pairs: what it got right, what it got wrong, and why |
| **What changes** | Not the model. The file the agent works from: instructions (Loop A) or a rubric of yes/no questions (Loop B) |

**The loop learns if its final file scores higher on P than its starting file.** Section 5 is where that happens.

---

## 3\. The hypothesis

> **Jev makes an agentic self-learning loop better.**

"Better" means either:

1. **It learns more:** higher accuracy on sealed pairs, or  
2. **It learns as well, far cheaper:** same accuracy at a fraction of the cost per decision.

**Why Jev might help:** Jev answers each rubric question separately. That tells the learner *which criterion* was wrong and by how much. An LLM picking the winner only tells the learner "right" or "wrong." The bet is that sharper feedback plus a cheap decider makes a better learner.

Verdict rules are fixed before running (Section 8).

---

## 4\. The atomic unit: one pair

Both loops get the **same pair**: two real headlines from the same Upworthy test, where we know which got more clicks. Neither loop is told.

**Example pair:**

- **X:** "Nothing Prepared Me For This Mind-Bending NASA Video…" (real click rate 1.00%)  
- **Y:** "NASA's Computers Reveal The Secret Life Of Carbon…" (real click rate 0.42%)

### Loop A (LLM only): one question about the pair

The LLM gets its instructions file plus both headlines:

> *\[instructions file\]* Headline X: "Nothing Prepared Me…" Headline Y: "NASA's Computers Reveal…" Which headline will more readers click? Answer X or Y, then give a one-line reason.

It answers "X: it creates curiosity without giving away the result." Code checks the answer key: correct.

The one-line reason is what Loop A learns from (5.3). This makes Loop A a strong baseline: LLMs are used for their reasoning, and the best LLM-only learning loops (Reflexion, GEPA) learn from the model's own reasoning. The reasons cost output tokens, which count toward Loop A's cost.

### Loop B (Jev rubric): yes/no questions about each headline

No LLM at this step. Jev gets one headline at a time plus the rubric's questions:

> Headline: "Nothing Prepared Me…"  
> 

> 1. Does it tease an outcome without revealing it? (yes/no)  
> 2. Does it name a specific person? (yes/no)  
> 3. …

Jev returns an answer and a probability for each question, for X and then for Y. **Code, not a model, turns them into a pick:**

- **Score \= sum of Jev's yes-probabilities** for "yes helps" questions, minus the sum for "yes hurts" questions.  
- Higher score wins. Any remaining exact ties are settled by a seeded coin flip, so every pair is simply right or wrong.  
- No weights, no fitted model. Kept simple on purpose.

**Why probabilities, not a count of yeses:** with 5 to 8 yes/no questions, two headlines would often get the same count (e.g. both tease the outcome, neither names a person). Every tie becomes a coin flip, which drags Loop B toward 50% while Loop A always commits to a pick. Summing probabilities almost never ties. **Log the tie rate** (share of pairs settled by coin flip) for every run.

---

## 5\. Where learning happens: the editor

**Jev never writes the rubric. It only answers questions.** An LLM (the editor) writes and rewrites the rubric. This is the most important part of the experiment: Jev makes each check cheap and makes per-question evidence possible, but if the editor is weak, Loop B can't learn.

### 5.1 Starting versions (version 0): fair start

The same LLM writes both starting versions from the same prompt:

> "You're an editor at a viral news site in 2014\. What makes a headline get more clicks?"  
> 

- **Loop A:** the answer, kept as prose instructions (up to 300 words).  
- **Loop B:** the same knowledge, written as 5 to 8 yes/no questions, each marked "yes helps" or "yes hurts."

Both loops start from the LLM's own general knowledge. Any later gap comes from learning, not from a head start. (Alexander does not hand-write the starting rubric.)

### 5.2 The evidence table (Loop B only; computed by code, free)

Jev has already answered every question for every practice headline. For the table, a headline counts as "yes" when Jev's yes-probability is at least 0.5. For each question, code counts:

- **Splits:** practice pairs where the two headlines got different answers.  
- **Win rate when split:** in those pairs, how often the "yes" headline won.

Example:

| Question | Splits | "Yes" won | Reading |
| :---- | :---- | :---- | :---- |
| Teases the outcome | 120 | 61% | useful |
| Names a person | 45 | 58% | weak but promising |
| Contains a number | 80 | 49% | no better than a coin flip |
| Addresses "you" | 3 | n/a | rarely applies |

A question can only help when it splits a pair. A win rate near 50% means it isn't predicting anything. A win rate well below 50% means its direction is backwards.

### 5.3 What each editor sees and does

|  | Loop A editor | Loop B editor |
| :---- | :---- | :---- |
| Current file | Instructions | Rubric |
| Score | Practice accuracy | Practice accuracy |
| Mistakes | 20 pairs it got wrong: both headlines, what it picked, which won | 20 pairs it got wrong: both headlines, what it picked, which won |
| Extra evidence | **Its own one-line reason for each of those 20 picks** | The evidence table (5.2) |
| History | Past changes and whether the gate kept them | Same |
| Allowed changes | Rewrite parts of the instructions | **Drop** a question; **flip** its direction; **reword** it; **add** 1 to 2 new ones based on what winners in the mistakes share |
| Limits | At most 3 changes; 300 words max | At most 3 changes; 10 questions max |
| Must output | The new file, plus one line per change saying why | The new file, plus one line per change citing the evidence table |

**Why the limits:** small, explained changes make it possible to see which change helped. Equal limits keep the loops comparable.

**What the comparison really tests:** Loop A learns from the LLM's own free-text reasoning. Loop B learns from structured per-question evidence. The question is whether Jev's structured evidence beats the LLM's reasoning, or matches it at a fraction of the cost.

**Example Loop A edit:** "In 6 of these mistakes I picked the more informative headline, but the winner teased a surprise. Adding: prefer headlines that hold back the outcome."

### 5.4 Check new questions before trusting them (Loop B)

The editor may write vague questions Jev answers inconsistently. For each new or reworded question, ask Jev twice on 10 practice headlines. If the two runs disagree on more than 1 of 10, send the question back to the editor to reword once; if it still fails, drop it.

### 5.5 The gate: keep or discard

The new version runs on the **gate** set. Compare it with the current version pair by pair:

- **b** \= pairs the new version gets right and the old one gets wrong.  
- **c** \= pairs the old version gets right and the new one gets wrong.  
- Pairs both get right, or both get wrong, carry no information.

**Keep the new version if b is clearly larger than c:** a one-sided sign test on b vs c, p \< 0.10 (set in config). Otherwise keep the old version and record "tried X, didn't help" in the history the editor sees next round.

The threshold is lenient on purpose: with 300 gate pairs, a strict test would reject almost everything and stall learning. The sealed set (Section 7\) is the strict check.

### 5.6 One round, end to end

1. Current version decides every **practice** pair. Log everything.  
2. Code builds the feedback: accuracy, 20 mistakes, the evidence table (Loop B), change history.  
3. Editor proposes a new version (5.3).  
4. Loop B: Jev answers any new questions; run the check in 5.4.  
5. Gate decides (5.5).  
6. Repeat. **4 rounds** per loop.

At the end, run version 0 and the final kept version of each loop **once** on the **sealed** set. Those are the reported numbers.

---

## 6\. Controls

- **Chance:** 50%.  
- **Fake decider:** guesses at random. Must score about 50% through the full harness on every set. If not, the harness has a bug.  
- **Code-feature baseline (hour 1, no LLM):** code counts six simple things about each headline (length, question mark, contains a number, uses "you", uses "I" or "me", exclamation mark). Logistic regression, the most basic statistical model, learns how much each count pushes a headline toward winning, then predicts the winner. No LLM, no cost, runs in seconds. Trained on practice; scored on gate in hour 1 and **once on the sealed set at the end**, so it appears on the same chart as the loops.  
  - **Above 50%:** there's signal in the data, and it sets a bar the loops must beat to be worth their cost. If a six-feature model matches both loops, that's a finding in itself.  
  - **At 50%:** a warning, not a verdict. Surface counts carry no signal, but meaning (e.g. "teases a surprise") still might, and only an LLM or Jev can read that. Pause and let Alexander decide whether to run the loops anyway.  
- **Loop C (polish block):** the same rubric loop as B, but the questions are answered by an LLM instead of Jev (`system-one-adapter-python` exposes the same interface backed by an LLM). This separates "rubrics help learning" from "Jev specifically helps." **Don't claim "Jev" in the pitch without Loop C.**

---

## 7\. Data

### 7.1 The task is a config, not code

Build the harness so a task is described in `task.yaml`: data files, the item text field, how pairs are formed, the outcome column, and the starting prompt (5.1). **Upworthy is task \#1, not the design.** A second task later (lead qualification, ticket routing, content review, "which variant will win") should be a new config, not new code.

### 7.2 Upworthy filters (in order)

Local files: `upworthy-archive-datasets/` (OSF `jd64p`).

1. Drop the undeployed file entirely.  
2. Drop tests created **2013-06-25 to 2014-01-10** (known randomization problem).  
3. **Headline must be the only difference.** Within each test, keep only variants with the same image (`eyecatcher_id`) and, where present, the same `excerpt`, but different headlines. Each test showed variants of the same story to randomly assigned readers at the same time, so with image and excerpt fixed, the headline is the only systematic difference.  
4. Pair the **highest** and **lowest** click-rate headlines among those variants. One pair per test.  
5. Keep the pair only if both have at least 1,000 impressions and the gap is clear: two-proportion z-score of at least 2\.  
6. Randomize which headline is shown as X, with a fixed seed. Same order for every loop.

Print the count after each filter. If filter 3 leaves too few pairs, relax the excerpt condition first (keep same image), and note it in the results.

**Parsing:** text fields contain line breaks and HTML. Use pandas `read_csv`, never line-based tools. Strip HTML.

### 7.3 Sets

| Set | Source file | Pairs | Used |
| :---- | :---- | :---- | :---- |
| Practice | exploratory | 300 | every round |
| Gate | confirmatory | 300 | every round |
| Sealed | holdout | up to 500 | once, at the end |

Save the pair IDs of each set on first run. Never resample. If a file yields too few pairs, lower the z-score threshold to 1.5 and note it. Don't borrow pairs across files.

### 7.4 Honest limits

- **Size:** with 500 sealed pairs, this run can reliably detect a gap of about 4 to 5 points. It's a smoke test, not proof. Proof is rung 1 of the scale-up ladder.  
- **Thin signal:** effects in this archive are real but small. Both loops may land near chance.  
- **Age:** 2013 to 2015 audiences. The test asks "can the loop learn what this data says," not "what works today."  
- **The LLM may have seen this data before (call this out in results).** The Upworthy archive and papers about it have been public since 2019, so the LLM may have absorbed some winning headlines during training. That would inflate Loop A's scores, since Loop A's decider is the LLM. Loop B's decider is Jev, but its rubric is written by the same LLM. **Check:** if Loop A's version 0 scores unusually high on the sealed set (above about 70%), suspect memorization before treating it as a result, and say so in the write-up either way.

---

## 8\. Verdict rules (fixed before running)

All numbers come from the sealed set. Each pair is right or wrong (ties already settled by coin flip).

**Four checks:**

| Check | Test |
| :---- | :---- |
| **Signal:** is either loop better than guessing? | 95% interval of final accuracy sits above 50% |
| **Learning (Mitchell):** did the loop improve with experience? | Final vs version 0, paired test on the same pairs (McNemar), p \< 0.05 |
| **Better:** does B beat A? | Final B vs final A, paired test (McNemar), p \< 0.05 |
| **Same quality:** is B about as good as A? | 95% interval of (B − A) falls within ±3 points. The ±3 margin is a stated choice, not derived. |
| **Cheaper:** | B's cost per 1,000 decisions is at most one fifth of A's (anchored to a vendor-reported 7x to 20x cost advantage) |

**Apply the first row that matches:**

| Result | Verdict | Next step |
| :---- | :---- | :---- |
| Neither loop passes the signal check | **No signal in this task.** Says nothing about Jev. | Stop. Pick a task with stronger signal. |
| B learned, and B is better than A | **Jev loop learns better.** Strongest outcome. | Polish, run Loop C, then scale. |
| B learned, same quality as A, and cheaper | **Learns as well, far cheaper.** A real result. | Polish, run Loop C, then scale. |
| A is better than B | **Hypothesis weakened.** | Write up why. Check whether the editor used the evidence table. |
| Anything else | **Inconclusive** (usually too few pairs). | Rerun with a second seed, or go straight to rung 1 (more data). |

Also report, not for the verdict: the code-feature baseline's sealed accuracy (as a reference line), gate accuracy by round (the learning curve), how many edits each gate kept, and the final rubric with its change history.

---

## 9\. Build plan

> **How to build (from Alexander's "Hero Coding to Systematic Agentic Workflows" doc):**  
> 

> - **No single long session with the coding agent.** Work in bounded chunks that follow the time blocks in 9.5. Each chunk has one job and a "done when" check.  
> - **Fake decider first.** Before any real Jev or LLM call, the fake decider must score about 50% through the whole harness. It's the cheapest bug check available.  
> - **Something breaks → a separate, scoped fix.** Don't bolt the fix onto a struggling session.  
> - **At the end of each chunk:** check the output, log what happened, then start the next chunk fresh.

### 9.1 Engineering principles

1. **Tracer bullet** (*The Pragmatic Programmer*): one thin slice running end to end first, then thicken it. Kept code, not a throwaway spike.  
2. **Build-measure-learn** (Lean Startup): the smallest thing that answers the question.  
3. **YAGNI** ("you aren't gonna need it"): nothing beyond this brief until the result says it's needed.  
4. **Pre-registration:** Section 8 is fixed before the run. Don't change it after seeing numbers.  
5. **Clean seams** (ports and adapters): four separate pieces behind small interfaces: **decider** (fake, A, B, C), **editor**, **gate**, **logger**. Each can be swapped without a rewrite.

### 9.2 Code standards

- **One config file** (`config.yaml`) for models, seeds, set sizes, batch size, gate threshold, edit limits, prices. No magic numbers in code. Plus `task.yaml` (7.1).  
- **Disk cache** for every API call, keyed by a hash of its full input. Reruns are free and repeatable.  
- **Fake decider first** (Section 6).  
- **Small tests** (`pytest`) where a bug would silently change the verdict: filters, pairing, rubric scoring, tie rule, evidence table, gate decision, cost calculation.  
- **Append-only JSONL log** of every call (Section 10).  
- **Retries with backoff** on API errors. Failed calls are logged, never silently dropped.  
- **Fixed seeds** and **pinned model versions**.  
- **`README.md`**: how to set keys, rerun everything with one command, where results land.

**Suggested layout:**

jev-loop-mvp/        \# standalone repo root

  config.yaml

  task.yaml         \# Upworthy \= task \#1

  prep.py           \# data → pair files \+ code baseline

  deciders.py       \# fake, A (LLM), B (Jev rubric), C (LLM-answered rubric)

  evidence.py       \# evidence table (5.2)

  editor.py         \# starting versions (5.1) and edits (5.3, 5.4)

  gate.py           \# sign test (5.5)

  log.py            \# JSONL logger \+ cost tracker

  cache.py          \# disk cache

  run.py            \# one command: rounds \+ sealed eval \+ results.json

  tests/

  data/             \# saved pair IDs (not the raw archive)

  results/

  README.md

### 9.3 Tools and repos to reuse

| Tool | Used for |
| :---- | :---- |
| pandas | Loading and filtering the Upworthy CSVs |
| scikit-learn, scipy, statsmodels | Code baseline; z-score filter; sign test, McNemar, confidence intervals |
| `typesafe-sdk-python` | Calling Jev (directly or via OpenRouter `typesafe/jev-1.13`) |
| `system-one-adapter-python` | Same interface backed by an LLM: Loop C and the no-Jev fallback |
| `dbreunig/building-with-jev-skill` | Guidance for the editor prompt on writing good Jev questions |
| Upworthy researchers' split script | Model for fixed seeds and saved IDs |
| GEPA's prompt-rewriting loop | Reference for wording the editor prompt. **Read only, not a dependency.** |

**Why direct calls:** all calls go directly to the model APIs. Every API response already reports its tokens, so per-decision cost is a few lines of code.

### 9.4 Preflight (15 minutes)

- Create a **new standalone repo** (e.g. `jev-loop-mvp`). Everything lives there. Keep it clean enough to share.  
- `.gitignore`: `.env`, the raw Upworthy archive, caches and logs. Commit only saved pair IDs, code, configs and results. (Check the archive's licence before committing any of its text.)  
- API keys in `.env`. Never commit keys.  
- Python virtual environment with pinned dependencies (`requirements.txt`).

### 9.5 Build and run block (4 hours)

| Time | Work | Done when |
| :---- | :---- | :---- |
| 0:00 to 0:30 | Access check: one Jev call (OpenRouter `typesafe/jev-1.13`, or `typesafe-sdk-python`), one LLM call. Record price per million tokens for each. | Both return. **Kill check:** no Jev access in 30 minutes → run Loop B on `system-one-adapter-python` and label the run "rubric loop vs prompt loop." |
| 0:30 to 1:15 | `prep.py`: filters, pairs, three sets, saved IDs, counts per filter. Code-feature baseline on the gate set. | Pair files on disk. **Decision point:** if the baseline is at chance, tell Alexander before building the loops (a warning, not a stop; see Section 6). |
| 1:15 to 3:00 | Harness per 9.2: config, cache, logger, gate, fake decider first. Then deciders A and B, evidence table, editor (5.1 to 5.4). Tests. | Fake decider scores about 50%; tests pass; one full round runs for both loops. |
| 3:00 to 3:45 | Version 0 plus 4 rounds for both loops. Sealed evaluation of version 0 and final. | `results.json` written. |
| 3:45 to 4:00 | Apply Section 8\. Write the verdict in one paragraph. | Verdict written. |

**If a block overruns by 30 minutes, cut in this order:** rounds from 4 to 3; practice and gate from 300 to 200 pairs; Loop A batch size up. Never cut the sealed set, the verdict rules, the evidence table, or cost logging.

### 9.6 Polish block (4 hours, only after a "learns better" or "far cheaper" verdict)

| Time | Work |
| :---- | :---- |
| 4:00 to 5:00 | Run Loop C (LLM-answered rubric). |
| 5:00 to 6:00 | Second seed for all loops. Check the verdict holds. |
| 6:00 to 7:00 | Chart: sealed accuracy for version 0 and final, per loop, with chance and the code-feature baseline as reference lines, plus cost per 1,000 decisions. Small chart: gate accuracy by round. |
[line omitted from the public copy]

If the verdict is "no signal" or "weakened," spend the polish block on a short, honest write-up instead.

---

## 10\. What to log (per call, JSONL)

`run_id`, `loop` (A/B/C/fake), `round`, `set`, `pair_id`, `version_id`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `prediction`, `correct`, for Loop A the one-line reason, for Loop B the per-question answers and probabilities, and whether the pick was a coin-flip tie. Editor calls log their proposed changes and reasons; gate decisions log b, c and p.

**Cost reporting:**

- **Decision cost:** dollars per 1,000 decisions, final version, sealed set. The headline cost number.  
- **Learning cost:** total spent by the editor across rounds, reported separately.  
- Free-tier LLM → price its tokens at a named paid reference rate.  
- If a model changes mid-run, rerun.

---

## 11\. If it works: the scale-up ladder

One rung at a time, each only after the one below gives a clear result.

1. **Power:** full archive (thousands of pairs per set), 3 seeds. Turns a smoke test into evidence.  
2. **Honest gate:** Stats Engine-style gate plus placebo edits (v4 Section 8).  
3. **Second task:** a new `task.yaml` on a business decision with an outcome label. Tests whether the result generalizes beyond headlines.  
4. **Writer agent:** uses the learned rubric to write headlines, plus the contamination test (v4 Sections 7.3 and 8.6).  
5. **Cross-model transfer:** a rubric learned with one editing model, used with another.  
6. **Write-up:** blog post with the RL and Mitchell framing (v4 Section 13).

### 11.1 Parked idea: turn it into a contextual bandit (true RL framing)

**The honest distinction:** the MVP is closer to supervised learning than RL. Every pair is independent, and we know the right answer whatever the loop picked. That's labelled data. So the precise description is "supervised learning where the parameters are text, updated in batches."

**How to make it a contextual bandit:**

- **Pairs won't do it.** With two options, knowing whether your pick won tells you the other one lost, so the loop still sees the full answer.  
- **Use tests with 3 or more variants.** The loop picks one variant and sees only that variant's click rate. The others stay hidden. Now it only learns from the outcome of the action it took, which is the defining feature of a contextual bandit (the context is the story and its variants).  
- **Scoring:** replay-style offline evaluation on the archive, since every variant's real click rate is on record even though the loop is only shown one.  
- **Live version later:** the writer agent generates headlines and real traffic scores them.

**Why it's parked:** it changes the task, not just the framing. Worth doing after the MVP result exists, and a strong section for the blog post either way.

---

## 12\. Outreach plan

*Omitted from the public copy: a plan for sharing the result with a third party. Section numbers are kept so references elsewhere still resolve.*

---

## 13\. Decisions before starting

*Omitted from the public copy: a personal pre-run checklist (model pin, reference price, access route, repo name). Section numbers are kept so references elsewhere still resolve.*

---

## 14\. Out of scope today

Everything else in v4: the writer, the judge, findings reports, the HACA-style composite, early-warning metrics, time split, GA data, cross-model transfer, multi-tenant answers. All parked in `BRIEF-v4-parking-lot.md`.