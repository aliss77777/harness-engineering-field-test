"""Every figure shown in "The shape of learning" GIF, derived from the committed trajectory data. Standard library only.

    python3 v2/scripts/shape_of_learning_figures.py          # assert the figures, check numbers.json is current
    python3 v2/scripts/shape_of_learning_figures.py --write  # rewrite docs/img/shape-of-learning.numbers.json

Data: docs/policy_visuals/trajectories-data.js (80 sealed tasks, MiniMax M3, starting vs final playbook, checkpoint on
in both). That file is derived from raw run logs that are outside this repository, so this module can verify the
numbers on screen but cannot rebuild the data. The drawing code is make_shape_of_learning_gif.py, which imports this
module (it needs Pillow and ffmpeg; this module does not).
"""
import argparse
import json
import statistics
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_JS = ROOT / "docs" / "policy_visuals" / "trajectories-data.js"
NUMBERS_JSON = ROOT / "docs" / "img" / "shape-of-learning.numbers.json"

# scene name, seconds
SCENES = [('setup', 4.6), ('cards', 5.0), ('learned', 5.2), ('course', 3.8), ('closing', 4.2)]
DURATION_S = round(sum(d for _, d in SCENES), 2)

txt = DATA_JS.read_text()
DATA = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
BY_ID = {r['id']: r for r in DATA}
N = len(DATA)


def change(r): return r['after']['credit'] - r['before']['credit']
BETTER = sorted([r for r in DATA if change(r) > 1e-7], key=lambda r: r['id'])
WORSE = sorted([r for r in DATA if change(r) < -1e-7], key=lambda r: r['id'])
TIED = sorted([r for r in DATA if abs(change(r)) <= 1e-7], key=lambda r: r['id'])
def errs(a): return sum(1 for c in a if c.isupper())
def writes(a): return sum(1 for c in a if c.lower() == 'w')


MEAN_B = sum(r['before']['credit'] for r in DATA) / N
MEAN_A = sum(r['after']['credit'] for r in DATA) / N
PASS_B = sum(r['before']['passed'] for r in DATA)
PASS_A = sum(r['after']['passed'] for r in DATA)
WR_B = sum(writes(r['before']['actions']) for r in DATA)
WR_A = sum(writes(r['after']['actions']) for r in DATA)
ER_B = sum(errs(r['before']['actions']) for r in DATA)
ER_A = sum(errs(r['after']['actions']) for r in DATA)
HOLD_B = sum(r['before']['holds'] for r in DATA) / N
HOLD_A = sum(r['after']['holds'] for r in DATA) / N
HJOBS_B = {r['id'] for r in DATA if r['before']['holds'] > 0}
HJOBS_A = {r['id'] for r in DATA if r['after']['holds'] > 0}
TIED_DIFF = sum(r['before']['actions'] != r['after']['actions'] for r in TIED)
TIED_MED = statistics.median(abs(len(r['after']['actions']) - len(r['before']['actions'])) for r in TIED)
WR_PCT = round((WR_A / WR_B - 1) * 100)
ER_PCT = round((1 - ER_A / ER_B) * 100)


def half_up(x, places=2):
    return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


# every number printed in the GIF or the README is asserted against the claims ledger
assert N == 80 and len(BY_ID) == 80
assert sum(r['domain'] == 'finance' for r in DATA) == 40 and sum(r['domain'] == 'hr' for r in DATA) == 40
assert (len(BETTER), len(WORSE), len(TIED)) == (27, 8, 45)
assert round(MEAN_B, 3) == 0.573 and round(MEAN_A, 3) == 0.755
assert (PASS_B, PASS_A) == (23, 33)
assert (WR_B, WR_A, ER_B, ER_A) == (393, 582, 380, 262) and (WR_PCT, ER_PCT) == (48, 31)
assert (HOLD_B, HOLD_A) == (0.825, 0.1875)
assert (half_up(HOLD_B), half_up(HOLD_A)) == ('0.83', '0.19') and (len(HJOBS_B), len(HJOBS_A)) == (35, 9)
assert TIED_DIFF == 45 and TIED_MED == 9
for _id, _calls, _credit in [('finance:4038', (4, 33), (0.0, 1.0)), ('hr:5106', (51, 45), (0.67, 1.0))]:
    _r = BY_ID[_id]
    assert (len(_r['before']['actions']), len(_r['after']['actions'])) == _calls
    assert (round(_r['before']['credit'], 2), round(_r['after']['credit'], 2)) == _credit


def numbers():
    src = 'docs/policy_visuals/trajectories-data.js (80 sealed tasks, MiniMax M3, starting vs final playbook, checkpoint on)'
    f, h = BY_ID['finance:4038'], BY_ID['hr:5106']
    rows = [
        ('1 setup', 'I gave an AI agent 80 back-office jobs it had never seen (Finance and HR)', '40 finance + 40 hr', 'count by domain; the 80 sealed tasks were not used to select rules', src + '; docs/policy_visuals/BRIEF.md'),
        ('1 setup', 'Then I built a harness that taught it to rewrite its own playbook, and I ran the same jobs again', 'text', 'the harness is the learning loop: reads graded mistakes, proposes rules, keeps a rule only if it beats the current playbook on held-out tasks; model weights unchanged', 'README.md (How it did it)'),
        ('2 cards', 'finance:4038  4 calls -> 33, credit 0.00 -> 1.00, 7 error rings in final run', {'before_calls': len(f['before']['actions']), 'after_calls': len(f['after']['actions']), 'credit': [f['before']['credit'], f['after']['credit']], 'after_errors': errs(f['after']['actions'])}, 'len(actions); upper-case action letters = tool errors', src),
        ('2 cards', 'hr:5106  51 calls -> 45, credit 0.67 -> 1.00, 2 -> 1 errors', {'before_calls': len(h['before']['actions']), 'after_calls': len(h['after']['actions']), 'credit': [h['before']['credit'], h['after']['credit']], 'errors': [errs(h['before']['actions']), errs(h['after']['actions'])]}, 'len(actions); upper-case letters = tool errors', src),
        ('3 learned', 'Own the outcome (GOALS) / Act on company policy (VALUES)', 'text', 'round-1 rule: complete every required write; round-2 rule: read policy emails before writing. GOALS/VALUES tags are an analogy only.', 'docs/policy_visuals/README.md (learning rounds)'),
        ('3 learned', 'Average credit 0.573 -> 0.755 (80 jobs)', [round(MEAN_B, 6), round(MEAN_A, 6)], 'mean of credit over 80 tasks', src + '; docs/CLAIMS.md'),
        ('3 learned', '27 better · 8 worse · 45 tied', [len(BETTER), len(WORSE), len(TIED)], 'sign of (after.credit - before.credit), tolerance 1e-7', src),
        ('3 learned', 'Written by the agent from its graded mistakes. Tested before it was kept.', 'text', 'learning loop reads graded mistakes, proposes rules, keeps a rule only if it beats the current playbook on held-out tasks', 'README.md (How it did it); docs/CLAIMS.md'),
        ('4 course', '35 -> 9 jobs with at least one stop (red dots; green = no stop)', [len(HJOBS_B), len(HJOBS_A)], 'count(holds > 0); 28 dots flip red->green, 2 flip green->red', src),
        ('4 course', '0.83 -> 0.19 checkpoint stops per job', [HOLD_B, HOLD_A], 'mean of holds over 80 tasks (0.825 -> 0.1875, rounded half-up); both conditions had the checkpoint on; stops cap at 3', src),
        ('4 course', 'checkpoint held any change until the agent had read the policy emails', 'text', 'definition of the pre-write checkpoint', 'README.md (A checkpoint before every record-changing action)'),
        ('5 closing', 'Teams get better when humans and agents work together. It compounds when the agent’s side learns too. / Full write-up in comments.', 'text', 'framing line from the brief; no figures', 'docs/policy_visuals/BRIEF.md (section 10 copy)'),
        ('footer', 'MiniMax M3 · text playbook only, model weights unchanged / 80 sealed tasks, one run each · Benchmark: AutomationBench (Zapier) / Alex Liss · AI systems builder · Independent research', 'text', 'model weights were not updated; one run per task per condition', 'README.md; docs/policy_visuals/BRIEF.md'),
    ]
    out = [dict(scene=a, on_screen=b, value=c, derivation=d_, source=e) for a, b, c, d_, e in rows]
    return dict(generated_from='docs/policy_visuals/trajectories-data.js', duration_s=DURATION_S, figures=out)


def render_numbers_json():
    return json.dumps(numbers(), indent=2)


def write_numbers():
    NUMBERS_JSON.write_text(render_numbers_json())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--write', action='store_true', help='rewrite docs/img/shape-of-learning.numbers.json')
    args = ap.parse_args()
    if args.write:
        write_numbers()
        print('wrote', NUMBERS_JSON.relative_to(ROOT))
        return
    if NUMBERS_JSON.read_text() != render_numbers_json():
        sys.exit('docs/img/shape-of-learning.numbers.json is out of date; run with --write')
    print(f'{N} tasks: {len(BETTER)} better / {len(WORSE)} worse / {len(TIED)} tied; '
          f'credit {MEAN_B:.3f} -> {MEAN_A:.3f}; stopped jobs {len(HJOBS_B)} -> {len(HJOBS_A)}; '
          f'stops per job {HOLD_B} -> {HOLD_A}; writes {WR_B} -> {WR_A}; errors {ER_B} -> {ER_A}')
    print('figures match the claims ledger; numbers.json is current')


if __name__ == '__main__':
    main()
