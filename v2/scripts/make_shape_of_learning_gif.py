#!/usr/bin/env python3
"""Render "The shape of learning" (800x1000 GIF and MP4): "How an agent's path changes as it learns".

    python3 v2/scripts/make_shape_of_learning_gif.py --out-dir /tmp/sol        # frames, then GIF and MP4
    python3 v2/scripts/make_shape_of_learning_gif.py --preview 0 7 12 17 21     # preview_<t>.png into --out-dir
    python3 v2/scripts/make_shape_of_learning_gif.py --numbers-only             # rewrite numbers.json; no Pillow, no ffmpeg

Provenance. Every figure on screen comes from docs/policy_visuals/trajectories-data.js, through
shape_of_learning_figures.py (standard library only; CI runs it). That data file derives from raw run logs that are
outside this repository, so this script cannot rebuild it. The GIF committed at docs/img/shape-of-learning.gif is the
canonical copy. A re-render with different fonts or a different ffmpeg build will not be byte-identical, so the
script refuses to overwrite existing output files unless --force is given.

Needs (not in v2/requirements.txt): Pillow, ffmpeg on PATH, and two fonts.
  Inter (OFL), static OTFs named Inter-Regular.otf, -Medium, -SemiBold, -Bold, -ExtraBold. Set SOL_INTER_DIR to their folder
    (default /usr/share/fonts/opentype/inter).
  Bitstream Charter Bold (Type 1 .pfb, as packaged in Debian's fonts-urw-base35 / gsfonts-x11). Set SOL_CHARTER_BOLD to
    the file (default /usr/share/fonts/X11/Type1/c0632bt_.pfb) and, for a .ttc collection, SOL_CHARTER_BOLD_INDEX.
  Georgia is not redistributable, which is why Charter is used. No fonts are vendored here.
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shape_of_learning_figures import (BETTER, BY_ID, DATA, HJOBS_A, HJOBS_B, HOLD_A, HOLD_B, MEAN_A, MEAN_B, SCENES,
                                       TIED, WORSE, errs, half_up, write_numbers)

ROOT = Path(__file__).resolve().parent.parent.parent
S = 2                       # supersample
W, H = 800, 1000
FPS = 30

# ------------------------------------------------------------------ timeline (seconds)
START, END = {}, {}
_t = 0.0
for _n, _d in SCENES:
    START[_n], END[_n] = _t, _t + _d
    _t += _d
T = _t
XFADE = 0.3                 # closing -> hook cross-fade so the loop is seamless

# ------------------------------------------------------------------ palette (repo palette)
C = dict(
    bg=(16, 25, 35), surface=(23, 36, 49), surface2=(29, 46, 60), line=(50, 69, 84),
    text=(243, 241, 233), soft=(209, 217, 218), muted=(184, 195, 200),
    aqua=(128, 211, 208), orange=(246, 182, 110), rose=(245, 154, 157), blue=(169, 193, 231),
    search=(187, 198, 208), read=(85, 169, 178), write=(232, 154, 81), other=(104, 117, 134),
    error=(190, 84, 96), chip_bg=(25, 74, 75), chip_fg=(181, 235, 230),
    dim=(40, 58, 72),
)
KIND = {'s': 'search', 'r': 'read', 'w': 'write', 'o': 'other'}

# ------------------------------------------------------------------ fonts
INTER_DIR = os.environ.get('SOL_INTER_DIR', '/usr/share/fonts/opentype/inter')
CHARTER_B = os.environ.get('SOL_CHARTER_BOLD', '/usr/share/fonts/X11/Type1/c0632bt_.pfb')
CHARTER_INDEX = int(os.environ.get('SOL_CHARTER_BOLD_INDEX', '0'))
_fc = {}
def font(kind, size):
    key = (kind, size)
    if key not in _fc:
        inter = {'i': 'Regular', 'im': 'Medium', 'is': 'SemiBold', 'ib': 'Bold', 'ie': 'ExtraBold'}
        if kind == 'cb':
            path, index, need = CHARTER_B, CHARTER_INDEX, 'Bitstream Charter Bold (set SOL_CHARTER_BOLD, and SOL_CHARTER_BOLD_INDEX for a .ttc)'
        else:
            path, index, need = os.path.join(INTER_DIR, f'Inter-{inter[kind]}.otf'), 0, 'Inter static OTFs (set SOL_INTER_DIR to their folder)'
        try:
            _fc[key] = ImageFont.truetype(path, int(round(size * S)), index=index)
        except OSError:
            sys.exit(f'font not found or unreadable: {path}\nInstall {need}. See the docstring of {Path(__file__).name}.')
    return _fc[key]

def tw(s, f, track=0):
    return f.getlength(s) / S + track * max(0, len(s) - 1)

def wrap(s, f, width):
    out, cur = [], ''
    for word in s.split():
        trial = (cur + ' ' + word).strip()
        if tw(trial, f) <= width or not cur:
            cur = trial
        else:
            out.append(cur); cur = word
    if cur: out.append(cur)
    return out

# ------------------------------------------------------------------ drawing helpers
G = 1.0                     # per-scene fade multiplier
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, t1): return clamp((t - t0) / (t1 - t0))
def eo(p): return 1 - (1 - p) ** 3
def eio(p): return p * p * (3 - 2 * p)
def lerp(a, b, p): return a + (b - a) * p

def lc(color, a=1.0, under=None):
    under = under or C['bg']
    a = clamp(a * G)
    return tuple(int(round(u + (v - u) * a)) for u, v in zip(under, color))

def mix(c0, c1, p):
    return tuple(int(round(lerp(u, v, p))) for u, v in zip(c0, c1))

def rrect(d, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill, outline=outline, width=int(width * S))

def text(d, x, y, s, f, color, anchor='l', track=0):
    """baseline-anchored; anchor l / m / r"""
    total = tw(s, f, track)
    if anchor == 'r': x -= total
    elif anchor == 'm': x -= total / 2
    if track == 0:
        d.text((x * S, y * S), s, font=f, fill=color, anchor='ls')
        return
    cx = x
    for ch in s:
        d.text((cx * S, y * S), ch, font=f, fill=color, anchor='ls')
        cx += f.getlength(ch) / S + track

def runs(d, x, y, parts, a, under=None, anchor='l'):
    """a line made of (text, font, color) runs"""
    total = sum(tw(s, f) for s, f, _ in parts)
    if anchor == 'r': x -= total
    elif anchor == 'm': x -= total / 2
    for s, f, col in parts:
        d.text((x * S, y * S), s, font=f, fill=lc(col, a, under), anchor='ls')
        x += tw(s, f)

def para(d, x, y, s, f, color, a, width, lead, under=None):
    """wrapped paragraph; returns baseline of the last line"""
    for k, line in enumerate(wrap(s, f, width)):
        d.text((x * S, (y + k * lead) * S), line, font=f, fill=lc(color, a, under), anchor='ls')
        last = y + k * lead
    return last

def dot(d, cx, cy, r, fill, outline=None, width=0):
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill, outline=outline, width=int(width * S))

# ------------------------------------------------------------------ static layer: header + footer (always on screen, incl. frame 0)
FOOT_LINES = ['MiniMax M3 · text playbook only, model weights unchanged',
              '80 sealed tasks, one run each · Benchmark: AutomationBench (Zapier)']
NAME, TITLE = 'Alex Liss', 'AI systems builder'
SUBHEAD = 'How an agent’s path changes as it learns'

def build_base():
    im = Image.new('RGB', (W * S, H * S), C['bg'])
    d = ImageDraw.Draw(im)
    text(d, 40, 36, 'AGENTIC WORKFLOWS  ·  80 BACK-OFFICE JOBS', font('ie', 18), C['orange'], 'l', 1.8)
    text(d, 40, 98, 'The shape of learning', font('cb', 54), C['text'], 'l', -0.6)
    assert tw(SUBHEAD, font('im', 30)) <= 720
    text(d, 40, 146, SUBHEAD, font('im', 30), C['soft'])
    d.line([(40 * S, 893 * S), (760 * S, 893 * S)], fill=C['line'], width=S)
    for k, ln in enumerate(FOOT_LINES):
        assert tw(ln, font('i', 18)) <= 720, ln
        text(d, 40, 918 + k * 23, ln, font('i', 18), C['muted'])
    runs(d, 40, 975, [(NAME, font('is', 20), C['text']), ('  ·  ' + TITLE + '  ·  Independent research', font('i', 20), C['muted'])], 1.0)
    return im
BASE = None

# ------------------------------------------------------------------ ribbon + card
def ribbon(d, x, y, w, h, actions, max_calls, n, a, under):
    rrect(d, x - 4, y - 4, x + w + 4, y + h + 4, 6, fill=lc(C['surface2'], a, under))
    unit = w / max_calls
    full, frac = int(n), n - int(n)
    for i, ch in enumerate(actions):
        if i > full or (i == full and frac <= 0):
            break
        wd = (unit - 1.6) * (frac if i == full else 1.0)
        if wd < 0.4: continue
        x0 = x + i * unit
        d.rounded_rectangle([x0 * S, y * S, (x0 + wd) * S, (y + h) * S], radius=1.6 * S, fill=lc(C[KIND[ch.lower()]], a, under))
        if ch.isupper() and i < full:
            r = min(6.5, unit * 0.32)
            dot(d, x0 + (unit - 1.6) / 2, y + h / 2, r, lc((255, 255, 255), a, under), lc(C['error'], a, under), 1.6)

def meta(actions, n):
    k = min(len(actions), int(n + 1e-9))
    e = errs(actions[:k])
    return f"{k} calls · {e} error{'' if e == 1 else 's'}"

def card(d, y0, row, a, dy, pb, pa, pc, chip_a, cap_a):
    if a <= 0: return
    y0 += dy
    x0, x1 = 40, 760
    panel = lc(C['surface'], a)
    rrect(d, x0, y0, x1, y0 + 262, 14, fill=panel, outline=lc(C['line'], a), width=1)
    b, af = row['before'], row['after']
    mx = max(len(b['actions']), len(af['actions']))
    f24 = font('is', 24)
    text(d, 64, y0 + 42, row['id'], f24, lc(C['text'], a, panel))
    text(d, 64 + tw(row['id'], f24) + 16, y0 + 42, 'Same job. Same model.', font('i', 18), lc(C['muted'], a, panel))
    chip_f = font('ie', 18)
    cw = tw('IMPROVED', chip_f, 1.0) + 24
    rrect(d, x1 - 24 - cw, y0 + 20, x1 - 24, y0 + 50, 15, fill=lc(C['chip_bg'], chip_a * a, panel))
    text(d, x1 - 24 - cw / 2, y0 + 41, 'IMPROVED', chip_f, lc(C['chip_fg'], chip_a * a, panel), 'm', 1.0)
    lab, mf = font('is', 18), font('i', 18)
    text(d, 64, y0 + 82, 'FIRST ATTEMPT', lab, lc(C['muted'], a, panel), 'l', 1.2)
    nb = pb * len(b['actions'])
    text(d, 736, y0 + 82, meta(b['actions'], nb), mf, lc(C['muted'], a, panel), 'r')
    ribbon(d, 68, y0 + 92, 664, 30, b['actions'], mx, nb, a, panel)
    text(d, 64, y0 + 154, 'AFTER THE PLAYBOOK UPDATE', lab, lc(C['muted'], a, panel), 'l', 1.2)
    na = pa * len(af['actions'])
    text(d, 736, y0 + 154, meta(af['actions'], na), mf, lc(C['muted'], a, panel), 'r')
    ribbon(d, 68, y0 + 164, 664, 30, af['actions'], mx, na, a, panel)
    text(d, 64, y0 + 238, f"{len(b['actions'])} calls → {len(af['actions'])}. Full credit.", font('is', 28),
         lc(C['text'], cap_a * a, panel))
    v = b['credit'] + (af['credit'] - b['credit']) * pc
    runs(d, 736, y0 + 240, [(f"{b['credit']:.2f} ", font('cb', 40), C['muted']), ('→ ', font('is', 28), C['muted']),
                            (f"{v:.2f}", font('cb', 40), C['aqua'])], a * (0.4 + 0.6 * clamp(pc * 4 + cap_a)), panel, 'r')

# ------------------------------------------------------------------ shared dot grid (scene 3 and scene 5 use identical positions)
PX, PY, DR = 46, 38, 13
GX0 = 400 - 13 * PX / 2
BANDS = [('CREDIT UP', BETTER, 'aqua', 366), ('CREDIT DOWN', WORSE, 'rose', 482), ('NO CHANGE', TIED, 'orange', 558)]
POS = {}
for _lab, _rows, _col, _y0 in BANDS:
    for _j, _r in enumerate(_rows):
        POS[_r['id']] = (GX0 + (_j % 14) * PX, _y0 + (_j // 14) * PY)

# ------------------------------------------------------------------ scenes (lt = seconds since the scene started)
def scene_setup(d, lt):
    """Frame 0 shows the whole screen (a complete LinkedIn preview); only the ribbon keeps filling in."""
    f32 = font('cb', 32)
    para(d, 40, 246, 'I gave an AI agent 80 back-office jobs it had never seen.', f32, C['text'], 1.0, 720, 42)
    text(d, 40, 346, 'Finance and HR work.', font('i', 24), lc(C['muted'], 1.0))
    text(d, 40, 416, 'Every job is a chain of steps:', f32, lc(C['text'], 1.0))
    x, y = 40, 460
    for word, key, tail in [('search', 'search', ', '), ('read', 'read', ', '), ('write', 'write', '.')]:
        d.rounded_rectangle([x * S, (y - 22) * S, (x + 16) * S, (y - 6) * S], radius=3 * S, fill=lc(C[key], 1.0))
        x += 24
        text(d, x, y, word, f32, lc(C[key], 1.0)); x += tw(word, f32)
        text(d, x, y, tail, f32, lc(C['text'], 1.0)); x += tw(tail, f32)
    text(d, 40, 548, 'Each mark is one step the agent took.', font('cb', 28), lc(C['text'], 1.0))
    acts = BY_ID['finance:4013']['before']['actions']
    ribbon(d, 68, 572, 664, 32, acts, len(acts), lerp(0.3, 1.0, eio(prog(lt, 0.9, 2.1))) * len(acts), 1.0, C['bg'])
    a4 = 1.0
    y4 = 690
    text(d, 40, y4, 'Then I built a harness that taught it', f32, lc(C['text'], a4))
    runs(d, 40, y4 + 44, [('to rewrite its own ', f32, C['text']), ('playbook', f32, C['orange']), (',', f32, C['text'])], a4)
    text(d, 40, y4 + 88, 'and I ran the same jobs again.', f32, lc(C['text'], a4))

def scene_cards(d, lt, a_out):
    e1 = eo(prog(lt, 0, 0.4))
    card(d, 204, BY_ID['finance:4038'], e1 * a_out, 16 * (1 - e1), prog(lt, 0.15, 0.45), eio(prog(lt, 0.45, 1.4)),
         eio(prog(lt, 1.2, 1.7)), prog(lt, 1.4, 1.7), eo(prog(lt, 1.4, 1.8)))
    l2 = lt - 1.6
    if l2 > 0:
        e2 = eo(prog(l2, 0, 0.4))
        card(d, 478, BY_ID['hr:5106'], e2 * a_out, 16 * (1 - e2), prog(l2, 0.15, 0.6), eio(prog(l2, 0.6, 1.6)),
             eio(prog(l2, 1.4, 1.9)), prog(l2, 1.6, 1.9), eo(prog(l2, 1.6, 2.0)))
    a3 = eo(prog(lt, 3.6, 4.0)) * a_out
    text(d, 40, 800 + 6 * (1 - a3), 'Sometimes longer. Sometimes shorter. Both improved.', font('cb', 28), lc(C['text'], a3))

def scene_learned(d, lt):
    a_h = eo(prog(lt, 0.0, 0.3))
    text(d, 40, 252 + 8 * (1 - a_h), 'What the agent taught itself.', font('cb', 36), lc(C['text'], a_h))
    items = [('Own the outcome.', '(Complete every step the job requires.)', 'GOALS', 0.3, 332),
             ('Act on company policy.', '(Check the company’s rules before taking action.)', 'VALUES', 1.0, 462)]
    for head, sub_, tag, t0, yh in items:
        a = eo(prog(lt, t0, t0 + 0.4))
        a_s = eo(prog(lt, t0 + 0.2, t0 + 0.6))
        d.rounded_rectangle([40 * S, (yh - 42) * S, 46 * S, (yh + 46) * S], radius=3 * S, fill=lc(C['aqua'], a))
        text(d, 66, yh + 8 * (1 - a), head, font('cb', 44), lc(C['text'], a), 'l', -0.4)
        tf = font('ie', 18)
        tww = tw(tag, tf, 1.6) + 28
        rrect(d, 760 - tww, yh - 34, 760, yh - 4, 15, outline=lc(C['aqua'], a), width=2)
        text(d, 760 - tww / 2, yh - 14, tag, tf, lc(C['aqua'], a), 'm', 1.6)
        text(d, 66, yh + 40, sub_, font('i', 24), lc(C['muted'], a_s))
    a_c = eo(prog(lt, 1.8, 2.2))
    para(d, 40, 568 + 6 * (1 - a_c), 'Written by the agent from its graded mistakes. Tested before it was kept.', font('is', 26),
         C['soft'], a_c, 700, 36)
    a_r = eo(prog(lt, 2.6, 3.0))
    d.line([(40 * S, 650 * S), (760 * S, 650 * S)], fill=lc(C['line'], a_r), width=S)
    text(d, 40, 690, 'RESULT ACROSS ALL 80 JOBS', font('ie', 18), lc(C['muted'], a_r), 'l', 1.6)
    mean = lerp(MEAN_B, MEAN_A, eio(prog(lt, 2.8, 3.7)))
    runs(d, 40, 758, [(f'{MEAN_B:.3f} ', font('cb', 52), C['muted']), ('→ ', font('is', 36), C['muted']),
                      (f'{mean:.3f}', font('cb', 52), C['aqua']), ('   average credit', font('is', 24), C['muted'])], a_r)
    a_t = eo(prog(lt, 3.5, 3.9))
    f34 = font('cb', 34)
    runs(d, 40, 820 + 6 * (1 - a_t), [(f'{len(BETTER)} better', f34, C['aqua']), (' · ', f34, C['muted']),
                                     (f'{len(WORSE)} worse', f34, C['rose']), (' · ', f34, C['muted']),
                                     (f'{len(TIED)} tied', f34, C['orange'])], a_t)

RED, GREEN = (240, 112, 118), (120, 208, 150)
JOBS = sorted(r['id'] for r in DATA)

def scene_course(d, lt):
    a_h = eo(prog(lt, 0.0, 0.3))
    text(d, 40, 250 + 8 * (1 - a_h), 'It needed fewer course-corrections.', font('cb', 34), lc(C['text'], a_h))
    tr = eio(prog(lt, 1.4, 1.9))
    a_lab = eo(prog(lt, 0.25, 0.6))
    a_l1, a_l2 = a_lab * (1 - tr), a_lab * tr
    lab = font('ie', 18)
    if a_l1 > 0.01: text(d, 40, 316, 'FIRST ATTEMPT', lab, lc(C['muted'], a_l1), 'l', 1.6)
    if a_l2 > 0.01: text(d, 40, 316, 'AFTER THE PLAYBOOK UPDATE', lab, lc(C['muted'], a_l2), 'l', 1.6)
    cols, px, py, r = 16, 44, 50, 17
    x0 = 400 - (cols - 1) * px / 2
    n_red = 0
    cells = []
    for k, jid in enumerate(JOBS):
        tf = 1.4 + 0.7 * ((k * 37) % 80) / 80          # when this dot flips (staggered permutation)
        vb, va = jid in HJOBS_B, jid in HJOBS_A
        red = va if lt >= tf else vb
        n_red += red
        pulse = 1 + 0.35 * math.sin(math.pi * prog(lt, tf, tf + 0.25)) if vb != va else 1.0
        cells.append((k, red, pulse))
    runs(d, 760, 322, [(f'{n_red}', font('cb', 34), RED if n_red > 20 else GREEN), (' of 80 jobs had a stop', font('is', 22), C['muted'])], a_lab, None, 'r')
    for k, red, pulse in cells:
        s = eo(prog(lt, 0.3 + k * 0.006, 0.55 + k * 0.006))
        if s <= 0: continue
        dot(d, x0 + (k % cols) * px, 392 + (k // cols) * py, r * (0.3 + 0.7 * s) * pulse, lc(RED if red else GREEN, s))
    a_k = eo(prog(lt, 0.6, 0.9))
    kf = font('i', 22)
    text(d, 40, 654, 'Each dot is one job.', font('is', 22), lc(C['soft'], a_k))
    x = 40 + tw('Each dot is one job.', font('is', 22)) + 34
    for col, label in [(RED, 'needed a stop'), (GREEN, 'no stop')]:
        dot(d, x + 7, 647, 7, lc(col, a_k))
        text(d, x + 22, 654, label, kf, lc(C['muted'], a_k))
        x += 22 + tw(label, kf) + 26
    a_n = eo(prog(lt, 0.9, 1.3))
    text(d, 40, 738, 'CHECKPOINT STOPS PER JOB', font('ie', 18), lc(C['muted'], a_n), 'l', 1.6)
    p_arrow = eo(prog(lt, 1.4, 1.7))
    hb = lerp(HOLD_B, HOLD_A, eio(prog(lt, 1.5, 2.2)))
    f58 = font('cb', 58)
    runs(d, 40, 792, [(half_up(HOLD_B), f58, C['muted'])], a_n)
    x2 = 40 + tw(half_up(HOLD_B) + ' ', f58)
    runs(d, x2, 792, [('→ ', font('is', 40), C['muted']), (half_up(hb), f58, GREEN)], a_n * p_arrow)
    a_s = eo(prog(lt, 2.0, 2.4))
    para(d, 40, 834 + 6 * (1 - a_s), 'A checkpoint held any change until the agent had read the company’s policy emails.',
         font('i', 24), C['soft'], a_s, 720, 32)

def scene_closing(d, lt):
    a1 = eo(prog(lt, 0.0, 0.4))
    para(d, 40, 372 + 8 * (1 - a1), 'Teams get better when humans and agents work together.', font('cb', 40), C['text'], a1, 720, 50)
    a2 = eo(prog(lt, 0.7, 1.1))
    para(d, 40, 502 + 8 * (1 - a2), 'It compounds when the agent’s side learns too.', font('cb', 32), C['aqua'], a2, 720, 44)
    a4 = eo(prog(lt, 1.4, 1.8))
    cf = font('is', 30)
    cw = tw('Full write-up in comments.', cf) + 56
    cy0 = 584 + 8 * (1 - a4)
    rrect(d, 40, cy0, 40 + cw, cy0 + 62, 31, fill=lc(C['text'], a4))
    pill = lc(C['text'], a4)
    text(d, 40 + cw / 2, cy0 + 42, 'Full write-up in comments.', cf, mix(pill, C['bg'], clamp(a4 * G)), 'm')

def legend(d, a):
    if a <= 0: return
    x, y, f = 40, 180, font('i', 18)
    for name, key in [('Search', 'search'), ('Read', 'read'), ('Write', 'write'), ('Other', 'other')]:
        d.rounded_rectangle([x * S, (y - 13) * S, (x + 14) * S, (y + 1) * S], radius=2 * S, fill=lc(C[key], a))
        text(d, x + 20, y, name, f, lc(C['muted'], a))
        x += 20 + tw(name, f) + 22
    dot(d, x + 7, y - 6, 7, lc((255, 255, 255), a), lc(C['error'], a), 1.6)
    text(d, x + 20, y, 'Tool error', f, lc(C['muted'], a))

# ------------------------------------------------------------------ frame
def _scene_frame(t):
    global G
    global BASE
    if BASE is None: BASE = build_base()
    im = BASE.copy()
    d = ImageDraw.Draw(im)
    out = lambda n: 1 - prog(t, END[n] - 0.3, END[n])
    G = 1.0
    legend(d, eo(prog(t, START['setup'] + 1.2, START['setup'] + 1.6)) * (1 - prog(t, END['cards'] - 0.3, END['cards'])))
    for name, fn in [('setup', scene_setup), ('learned', scene_learned), ('course', scene_course),
                     ('closing', scene_closing)]:
        if START[name] <= t < END[name] + 1e-9:
            G = 1.0 if name == 'closing' else out(name)
            fn(d, t - START[name])
    G = 1.0
    if START['cards'] <= t < END['cards']:
        scene_cards(d, t - START['cards'], out('cards'))
    return im

_F0 = None
def render(t):
    global _F0
    im = _scene_frame(t)
    if t >= T - XFADE:
        if _F0 is None: _F0 = _scene_frame(0.0)
        im = Image.blend(im, _F0, eio(prog(t, T - XFADE, T)))
    return im.resize((W, H), Image.LANCZOS)


# ------------------------------------------------------------------ output
BUILD_GIF = ['-vf', 'fps=15,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle', '-loop', '0']
BUILD_MP4 = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']

def build(out_dir, force):
    gif, mp4 = out_dir / 'shape-of-learning.gif', out_dir / 'shape-of-learning.mp4'
    if not force:
        taken = [p.name for p in (gif, mp4) if p.exists()]
        if taken:
            sys.exit(f'{", ".join(taken)} already exists in {out_dir}; the committed copy is canonical. Use another --out-dir or --force.')
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg not found on PATH')
    n = int(round(T * FPS))
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            render(i / FPS).save(os.path.join(tmp, f'f{i:04d}.png'))
        print('frames', n, 'duration', round(T, 2))
        src = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png')]
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(src + BUILD_GIF + [str(gif)], check=True)
        subprocess.run(src + BUILD_MP4 + [str(mp4)], check=True)
    print('wrote', gif, f'({gif.stat().st_size:,} bytes)'); print('wrote', mp4, f'({mp4.stat().st_size:,} bytes)')

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out-dir', type=Path, default=ROOT / 'docs' / 'img')
    ap.add_argument('--preview', nargs='+', metavar='SECONDS', help='write preview_<t>.png for these times instead of building')
    ap.add_argument('--numbers-only', action='store_true', help='rewrite docs/img/shape-of-learning.numbers.json and stop')
    ap.add_argument('--force', action='store_true', help='overwrite existing GIF and MP4')
    a = ap.parse_args()
    if a.numbers_only:
        write_numbers(); print('numbers.json written; duration', round(T, 2))
    elif a.preview:
        a.out_dir.mkdir(parents=True, exist_ok=True)
        for ts in a.preview:
            render(float(ts)).save(a.out_dir / f'preview_{ts}.png'); print('wrote', ts)
    else:
        build(a.out_dir, a.force)

if __name__ == '__main__':
    main()
