# The shape of learning — visualization brief

**Status:** working research and design brief · **Updated:** 21 October 2026

This document preserves the purpose, definitions, evidence boundaries, and next steps for the AutomationBench policy visualization work. Start here when continuing it in a later session. The [figure guide](README.md) explains the current artwork; the [topology audit](TOPOLOGY_ANALYSIS.md) contains the exploratory calculations; the [experiment design](../../v2/briefs/V2%20Phase%201%20Canonical%20Experiment%20Design.md), [results](../../v2/RESULTS.md), and [claims](../CLAIMS.md) govern statements about the underlying experiment.

## The question

**What changes in an agent's path through a task when an evaluated playbook revision improves its final result?** In particular:

1. Does a better run grow because it performs previously missing work, or shrink because it escapes an unproductive loop?
2. Are those path changes associated with the task's structure, the playbook revision, or an interaction between them?
3. Which observed changes are stable across independent runs, and which are ordinary run variation?
4. Where does behavior change without a score change, especially on tasks still not fully solved?

The ambition is an **RL-inspired visual policy analysis** of business-workflow agents: paired, same-task trajectories, a visible sequence of policy-selection rounds, and a cohort view that keeps exceptions visible. Here “policy” means the agent's *text playbook* chosen by a harness. The model weights were not updated. The logs contain sampled tool calls and final grades, not an action-probability distribution, per-step rewards, or a learned value function. The figures must keep that distinction legible.

## First principles

1. **Pair by task.** Compare the same task ID under the starting and final playbooks. Keep the model, task, and relevant harness condition fixed within a displayed pair. Label the condition whenever it changes.
2. **Show behavior and outcome together.** A tool-call path is useful only alongside its final credit, pass status, and, where available, scored-check detail. More writes or fewer calls do not automatically mean better work.
3. **Preserve order and scale.** One ribbon mark is one executed tool call, in sequence. Relative lengths within a pair must reflect actual call counts. Search/read/write/other and tool errors are observable categories; they are not physical coordinates or a semantic judgment of correctness.
4. **Let the cohort challenge the example.** Opening examples may clarify an idea, but every gain, regression, and unchanged score must remain findable in the full atlas. The current opening pair deliberately shows one longer and one shorter improvement, not the most typical tasks.
5. **Separate selection from evaluation.** The 60-task gate chose rules and supports a policy-search trace. The 80 sealed tasks give a before/after bookend. A gate trend is not an independent generalization estimate; using sealed outcomes to invent a new intervention makes those tasks exploratory for that intervention.
6. **Show uncertainty at the right level.** MiniMax's runs vary even at temperature zero. A single task ribbon is an example, not an estimate of the playbook's task-specific effect. Repeats under every compared playbook are needed to separate a stable response from run noise.
7. **Keep source content out of public visuals.** The committed atlas contains task IDs, action categories, error markers, credit, pass status, and hold counts. It does not contain prompts, tool arguments, tool results, hidden assertions, or policy-email text.

## Data and terms

The visual generator reads the full JSONL run logs at `/Users/alexanderliss/Documents/jev-test-poc/v2/logs/phase1_run/`. Those logs are **outside this repository**. The repository commits derived figures and a compact action-category atlas so the demo works offline; recreating the figures from source requires access to the original logs and the pinned AutomationBench environment. The experiment's committed `sealed_runs.csv` contains summary rows but not ordered calls.

| Term | Meaning in these visuals |
| --- | --- |
| Before / after | MiniMax M3 with the starting / final retained text playbook on the same sealed task; both have the pre-write checkpoint on. |
| Learning round | A proposal and gate evaluation that may or may not change the retained playbook. Four rounds produced three distinct retained versions. |
| Ribbon length | Number of executed tool calls, including calls that returned errors. |
| Search / read / write / other | `api_search`; `api_fetch` with `GET`; `api_fetch` with another method; all other tool names. “Write” counts an attempt, not a confirmed state change. |
| Error ring | A tool result containing an `error` object. |
| Hold | A pre-write checkpoint intervention. The log records its model step, so current ribbons show a total rather than placing it among executed calls. |
| Improved / declined / no change | Sign of the change in final partial credit, with a small numeric tolerance in the atlas. These labels do not describe ribbon length. |
| Full pass | The task's final-state grade reports `passed`; partial credit and checks provide additional detail. |

For the 80 sealed pairs, **27 improved, 8 declined, and 45 had no credit change**. The no-change group contains 19 tasks already at full credit, 22 still partially solved, and 4 still at zero. A tied grade often conceals a different action path. This is a productive diagnostic split, not evidence that the same intervention would fix all 26 unresolved ties.

## Current artifact map

| Artifact | Purpose |
| --- | --- |
| [Guided demo](demo.html) | Six-chapter narrative combining the principal figures and limits. |
| [All trajectories](trajectories.html) and [compact data](trajectories-data.js) | Every sealed before/after ribbon, grouped by Finance and HR, with outcome filters. |
| [Paired ribbons](action-ribbons.svg) | Opening examples: `finance:4038` grows and `hr:5106` shortens; both improve to full credit. |
| [Learning ribbons](learning-ribbons.svg) and [policy search](policy-search.svg) | Matched gate-task paths across retained versions and the selected/unselected proposals. |
| [Action-space portraits](action-space-portraits.svg) and [cohort atlas](cohort-atlas.svg) | Count-based path portraits and all-task context. |
| [Mechanism chart](ribbon-mechanisms.svg) and [topology audit](TOPOLOGY_ANALYSIS.md) | Descriptive action-mix motifs, weak task-text/topology predictions, and same-playbook repeatability. |
| [Animated summary](../img/shape-of-learning.gif) ([MP4](../img/shape-of-learning.mp4)) and [on-screen figures](../img/shape-of-learning.numbers.json) | 22.8-second explainer of figures A, C, D and the checkpoint-stop counts; every figure on screen with its derivation and source. |
| [GIF generator](../../v2/scripts/make_shape_of_learning_gif.py) and [figures check](../../v2/scripts/shape_of_learning_figures.py) | Re-render the GIF and MP4 from `trajectories-data.js`; the standard-library check asserts the figures and runs in CI. The committed GIF is canonical. |
| [Visual generator](../../v2/scripts/explore_policy_visuals.py) and [audit generator](../../v2/scripts/analyze_ribbon_topology.py) | Rebuild derived assets from the source logs. |

## What we have learned, and what remains open

Improving longer ribbons generally add work, especially writes; improving shorter ribbons often shed repeated reads and errors. The **composition** shift is clearer across sets than a universal length direction. Coarse task features and prompt TF-IDF gave weak held-out discrimination of growth versus shortening (AUC 0.59 and 0.57). Starting ribbon length predicted direction more strongly, but it is mathematically coupled to `after − before` and cannot be read as a task-topology cause. On the 60 gate tasks, two same-final-playbook repeats differed by a median of seven calls. The checkpoint fired less often under the final playbook: stops per job fell from 0.825 to 0.1875 and the number of jobs with at least one stop from 35 to 9, with the checkpoint on in both conditions. This is consistent with the playbook absorbing the habit; the experiment's claims say the checkpoint looks like a training scaffold and was not shown to be worth keeping at exam time (0.755 on, 0.775 off), so do not read the drop as the checkpoint causing the gain. See the [audit](TOPOLOGY_ANALYSIS.md) for denominators and limitations.

The next topology representation should be **structured**, not a generic phrase cloud: connect a task to required actions, forbidden actions, services, objects, and dependencies such as “read policy before write”; represent a run as a directed, time-ordered action and service graph. The nearby `/Users/alexanderliss/Documents/NLP-graph-analysis` project offers a useful bipartite-graph construction idea, but its phrase-extraction pipeline is tuned for a much larger B2B text corpus and has not been validated for these workflows.

The most actionable unsolved cohort is the **26 no-change tasks below full credit** (19 Finance, 7 HR). Among those tasks, 17 have at least one broken-rule check and 13 have at least one wrong-content check; those groups overlap. A candidate harness experiment is to verify proposed record changes against extracted required values and prohibitions before execution. This is a hypothesis from sealed-task diagnostics, not a measured gain. Evaluate it on fresh tasks or a new held-out split rather than claiming a second sealed result on the same 80.

## Continuation protocol

1. **Verify the comparison.** Record model, playbook version, checkpoint state, task set, run count, and grading version for every new figure. Preserve task pairing.
2. **Choose a question before a visual encoding.** Examples: “Which requirements were missed despite more writes?” or “Does cross-service dependency depth predict a playbook response?” Decide the unit of analysis and comparison before picking attractive paths.
3. **Build the cohort view first.** Calculate domain and outcome denominators; find ceiling, floor, and partial-credit ties; inspect regressions. Choose examples only after seeing this distribution, then label them as selected.
4. **Separate observed, inferred, and proposed.** Tool order and final grades are observed. Claims about loops or task topology are interpretations. Causal claims require an experiment with repeats and a comparison set outside rule selection.
5. **Run a repeat-aware test for mechanism claims.** The preferred design crosses tasks × retained playbooks × independent repeats, with a fresh evaluation set. Analyze grade and path features together; report uncertainty at the task level.
6. **Regenerate and verify.** Rebuild figures from logs, check 80 unique sealed IDs with 40 Finance and 40 HR, verify 27/8/45 outcome counts, parse every SVG, and exercise atlas filters. Keep raw prompts, tool payloads, and hidden checks out of committed assets.
7. **Update this brief when the meaning changes.** Add new questions, encodings, evidence limits, and data provenance here; update the figure guide for new artifacts. Keep the original experiment's results and claims documents as the authority on what the benchmark established.

From the repository root, rebuild the current assets with:

```bash
python3 v2/scripts/explore_policy_visuals.py \
  --logs /Users/alexanderliss/Documents/jev-test-poc/v2/logs/phase1_run

PYTHONPATH=v2/src:v2/scripts \
  /Users/alexanderliss/Documents/jev-test-poc/v2/.venv/bin/python \
  v2/scripts/analyze_ribbon_topology.py \
  --logs /Users/alexanderliss/Documents/jev-test-poc/v2/logs/phase1_run
```
