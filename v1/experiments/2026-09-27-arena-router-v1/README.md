# Experiment 5: route between Jev and the LLM — Results

**Completed:** 2026-09-27 · **Brief:** [`config/Task Brief 5_Routing.md`](config/Task%20Brief%205_Routing.md) · **Preregistered verdict:** **Same quality, half the cost**

## Headline

> On 1,000 fresh Chatbot Arena battles, a router that let a learned Jev rubric decide the 62% of cases it was confident about, and sent only the rest to the LLM, matched the LLM's accuracy (76.2% vs 76.3%; 95% interval of the difference −1.8 to +1.6 points) at 43% of its cost per decision ($0.63 vs $1.48 per 1,000) and about a third less latency.

Wording rules carried over from the MVP brief: say "a yes/no rubric" rather than "Jev" until Loop C is run; the LLM's memorization flag is on (76.3% > 70%). Scope: one decision task, 2023–2024 Arena single-turn battles.

## Setup

- **LLM:** experiment 2's final Loop A (`A-r1-c2`), Gemini 3.8 Flash.
- **Jev:** experiment 3's B-plus final (`Bw-r4-c1`, six questions, fitted weights), Jev 1.13.
- **Router:** Jev scores every pair. If |Jev's weighted score| ≥ τ, Jev's pick is final. Otherwise the LLM decides; if Gemini refuses the pair, Jev's pick is used.
- **τ = 0.4453**, preregistered as the gate-set quantile that sends 40% of pairs to the LLM (a fixed budget, not tuned for accuracy). Frozen before the sealed set was read ([`artifacts/router_model.json`](artifacts/router_model.json)). On gate, the router scored 75.2% vs the LLM's 77.1%.
- **Sealed-5:** 1,000 fresh pairs excluding all 4,000 earlier sealed pairs; no pair or prompt overlap with practice, gate or earlier sealed sets; winner first in exactly 50%. Evaluated once.

## Results (sealed-5, 1,000 pairs)

| System | Accuracy | 95% interval | Cost / 1,000 decisions | Avg latency / decision |
|---|---:|---:|---:|---:|
| LLM alone | 76.3% | 73.6–78.8% | $1.481 | 1,285 ms |
| Jev alone | 72.7% | — | $0.065 | 384 ms |
| **Router** | **76.2%** | 73.5–78.7% | **$0.633** | **874 ms** |
| Style code baseline | 59.9% | — | $0 | — |

- **Primary, router vs LLM:** 36 pairs better, 37 worse; McNemar p = 1.0. The 95% interval of (router − LLM) is **−1.8 to +1.6 points**, inside ±3. Cost ratio **0.43** (≤ 0.5). → **Same quality, half the cost.**
- **Router vs Jev alone:** router better (85 vs 50, p 0.003).
- **All systems vs the style baseline:** all clearly better (p < 0.0001).
- **Routing:** 38.2% of pairs went to the LLM (40% on gate), 1 of which Gemini refused (Jev decided it).

### Why it works

| Pairs | Share | Router accuracy | LLM accuracy on the same pairs |
|---|---:|---:|---:|
| Jev confident (Jev decides) | 61.8% | **81.6%** | 81.7% |
| Jev unsure (LLM decides) | 38.2% | 67.5% | 67.5% |

On the pairs where the rubric is confident, it is as accurate as the LLM (81.6% vs 81.7%), so paying for the LLM there buys nothing. The LLM earns its cost only on the harder, closer calls.

**Accuracy vs LLM share** (same decisions, whole curve): 0% 72.7 · 10% 74.1 · 20% 75.1 · 30% 75.9 · **40% 76.1** · 50% 75.8 · 60–90% 75.9–76.1 · 100% 76.3. Beyond about 30–40%, extra LLM calls add almost nothing.

## Relation to experiment 4

Experiment 4's stacked vote (both systems on every pair) matched the LLM but cost more. Its exploratory cascade suggested routing would keep accuracy at half the cost. This experiment preregistered that idea, froze the threshold on gate, and confirmed it on a new sealed set.

## Run integrity and cost

- Design and code committed before any paid call (`4fd7f29`); τ frozen and committed (`d78bf1a`) before the sealed set was read.
- The first sealed attempt stopped on OpenRouter 402 (the API key's own $50 limit) after about 150 pairs; it wrote no verdict. After the key limit was raised, attempt 2 resumed from cache and completed.
- Paid spend: τ fit $0.00 (cache); sealed $1.54. **Total: $1.54.**

## Limits

One task; LLM memorization flag on (the router inherits it on routed pairs); τ set on a gate set used before, and the 40% budget was informed by experiment 4's sealed-4 curve (disclosed; sealed-5 is new); ±3 points is a stated margin; costs are per-pair shares of 5-pair LLM batches (a deployment would batch only routed pairs).

## Files

[`artifacts/sealed_complete.json`](artifacts/sealed_complete.json) (verdict, tests, routing split, curve, latency) · [`artifacts/router_model.json`](artifacts/router_model.json) (τ and gate numbers) · `config/` · `splits/` (sealed-5 IDs) · `telemetry/`.
