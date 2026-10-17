"""Make three exploratory, content-free views of paired AutomationBench runs.

Usage:
  python3 v2/scripts/explore_policy_visuals.py --logs /path/to/v2/logs/phase1_run

Only action type, task ID, and final grade leave the source logs. The script never
copies prompts, tool arguments, tool results, summaries, or hidden assertions.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path


BEFORE = "minimax-p1-v0-cp-sealed.jsonl"
AFTER = "minimax-p1-s78766c8a-cp-sealed.jsonl"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "policy_visuals"
INK = "#233042"
MUTED = "#687586"
GRID = "#dce2e8"
BEFORE_COLOR = "#798694"
AFTER_COLOR = "#157e9b"
SEARCH = "#bbc6d0"
READ = "#55a9b2"
WRITE = "#e89a51"
ERROR = "#be5460"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(x: float, y: float, value: object, *, size: int = 14, color: str = INK,
         anchor: str = "start", weight: int = 400) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{esc(value)}</text>')


def line(x1: float, y1: float, x2: float, y2: float, *, color: str = GRID,
         width: float = 1, dash: str = "") -> str:
    attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{width}"{attr}/>')


def circle(x: float, y: float, radius: float, *, fill: str, stroke: str = "none") -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}" stroke="{stroke}"/>'


def rect(x: float, y: float, width: float, height: float, *, fill: str) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
            f'height="{height:.1f}" fill="{fill}"/>')


def svg(width: int, height: int, title: str, body: list[str]) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><rect width="100%" height="100%" fill="white"/>'
            + "".join(body) + "</svg>\n")


def read_runs(path: Path) -> dict[str, dict]:
    rows = (json.loads(raw) for raw in path.open(encoding="utf-8"))
    return {row["task_id"]: row for row in rows if row.get("event") == "candidate_run"}


def kind(call: dict) -> str:
    if call.get("name") == "api_search":
        return "search"
    if call.get("name") != "api_fetch":
        return "other"
    method = str((call.get("args") or {}).get("method", "GET")).upper()
    return "read" if method == "GET" else "write"


def failed(call: dict) -> bool:
    try:
        payload = json.loads(call.get("result", ""))
    except (TypeError, ValueError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("error"), dict)


def counts(run: dict) -> dict[str, int]:
    result = {"search": 0, "read": 0, "write": 0, "other": 0, "error": 0}
    for call in run["calls"]:
        result[kind(call)] += 1
        result["error"] += failed(call)
    return result


def grade(run: dict) -> str:
    return f'{run["partial_credit"]:.2f} credit · {"pass" if run["passed"] else "fail"}'


def unmet_checks(run: dict) -> str:
    missed = [check for check in run["checks"] if not check["passed"]]
    if not missed:
        return "none"
    names = {"rule_broken": "must-not", "wrong_content": "content", "action_missed": "required action"}
    kinds = {kind: sum(check["kind"] == kind for check in missed)
             for kind in ("rule_broken", "wrong_content", "action_missed")}
    detail = ", ".join(f"{count} {names[kind]}" for kind, count in kinds.items() if count)
    return f"{len(missed)} ({detail})"


def ribbons(before: dict, after: dict) -> str:
    selected = ["finance:4038", "hr:5106"]
    width, height = 1280, 445
    body = [text(36, 37, "A  ·  Paired action ribbons", size=23, weight=500),
            text(36, 64, "One mark = one executed tool call; hollow red rings = tool errors. Checkpoint holds are listed separately.", size=13, color=MUTED)]
    for label, color, x in [("Search", SEARCH, 44), ("Read", READ, 135),
                            ("Write", WRITE, 212), ("Other", MUTED, 292)]:
        body += [rect(x, 83, 15, 15, fill=color), text(x + 22, 96, label, size=13)]
    body += [circle(379, 90, 6, fill="white", stroke=ERROR), text(393, 96, "Error", size=13)]
    x0, x1 = 180, 865
    for group, task_id in enumerate(selected):
        y_top = 136 + group * 145
        body += [text(36, y_top, task_id, size=17, weight=500)]
        max_calls = max(len(before[task_id]["calls"]), len(after[task_id]["calls"]))
        unit = (x1 - x0) / max_calls
        for offset, (label, run) in enumerate([("Before", before[task_id]), ("After", after[task_id])]):
            y = y_top + 26 + offset * 38
            body += [text(36, y + 11, label, size=14), line(x0, y + 17, x1, y + 17)]
            for i, call in enumerate(run["calls"]):
                x = x0 + i * unit
                color = {"search": SEARCH, "read": READ, "write": WRITE}.get(kind(call), MUTED)
                body += [rect(x, y, max(2.4, unit - 0.8), 20, fill=color)]
                if failed(call):
                    body += [circle(x + max(2.4, unit - 0.8) / 2, y + 10, 5,
                                    fill="white", stroke=ERROR)]
            passed = sum(check["passed"] for check in run["checks"])
            body += [text(886, y + 11,
                          f'{grade(run)} · {passed}/{len(run["checks"])} checks · {len(run["calls"])} calls · {run["holds"]} holds',
                          size=12)]
        body += [text(x0, y_top + 113,
                      f'Unmet checks — before: {unmet_checks(before[task_id])}; after: {unmet_checks(after[task_id])}',
                      size=12, color=MUTED),
                 line(36, y_top + 128, 1244, y_top + 128)]
    body += [text(180, 436, "Executed tool call number →", size=13, color=MUTED)]
    return svg(width, height, "Paired action ribbons for two AutomationBench tasks", body)


def portraits(before: dict, after: dict) -> str:
    selected = ["finance:4038", "hr:5106", "finance:4030", "hr:5091"]
    width, height = 1160, 705
    body = [text(36, 38, "B  ·  Action-space portraits", size=23, weight=500),
            text(36, 65, "Each path begins at zero. Horizontal steps are search/read calls; vertical steps are write calls.", size=13, color=MUTED)]
    for label, color, x in [("Before", BEFORE_COLOR, 705), ("After", AFTER_COLOR, 790)]:
        body += [line(x, 91, x + 21, 91, color=color, width=3), text(x + 28, 96, label, size=13)]
    for n, task_id in enumerate(selected):
        col, row = n % 2, n // 2
        left = 72 + col * 558
        top = 138 + row * 275
        pw, ph = 442, 195
        ax, ay = left + 35, top + ph
        xmax = max(sum(kind(c) in ("search", "read") for c in r["calls"])
                   for r in (before[task_id], after[task_id])) or 1
        ymax = max(sum(kind(c) == "write" for c in r["calls"])
                   for r in (before[task_id], after[task_id])) or 1
        body += [text(left, top - 15, task_id, size=16, weight=500),
                 line(ax, top, ax, ay), line(ax, ay, ax + pw, ay)]
        for fraction in (0.5, 1):
            body += [line(ax, ay - ph * fraction, ax + pw, ay - ph * fraction, dash="3 4"),
                     line(ax + pw * fraction, top, ax + pw * fraction, ay, dash="3 4")]
        body += [text(ax, ay + 19, "0", size=11, color=MUTED, anchor="middle"),
                 text(ax + pw, ay + 19, str(xmax), size=11, color=MUTED, anchor="middle"),
                 text(ax - 8, top + 4, str(ymax), size=11, color=MUTED, anchor="end")]
        for run, color in [(before[task_id], BEFORE_COLOR), (after[task_id], AFTER_COLOR)]:
            information = writes = 0
            points = [(ax, ay)]
            for call in run["calls"]:
                category = kind(call)
                information += category in ("search", "read")
                writes += category == "write"
                points.append((ax + pw * information / xmax, ay - ph * writes / ymax))
            path = " ".join(f'{"M" if j == 0 else "L"}{x:.1f},{y:.1f}'
                            for j, (x, y) in enumerate(points))
            body += [f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" '
                     'stroke-linecap="round" stroke-linejoin="round"/>',
                     circle(*points[-1], 5, fill=color),
                     text(ax + pw + 8, points[-1][1] + (10 if color == BEFORE_COLOR else -4),
                          f'{run["partial_credit"]:.2f}', size=12, color=color)]
        body += [text(ax + pw / 2, ay + 39, "Search + read calls →", size=12, color=MUTED, anchor="middle"),
                 text(left, top + ph / 2, "Write calls ↑", size=12, color=MUTED)]
    body += [text(36, 685, "Counts locate behavior in action space; neither axis is physical position or evidence quality.",
                  size=13, color=MUTED)]
    return svg(width, height, "Action-space portraits of four matched tasks", body)


def atlas(before: dict, after: dict) -> str:
    selected = ["finance:4038", "hr:5106", "finance:4030", "hr:5091"]
    rows = []
    for task_id in before.keys() & after.keys():
        first, last = before[task_id], after[task_id]
        rows.append((task_id, counts(last)["write"] - counts(first)["write"],
                     last["partial_credit"] - first["partial_credit"]))
    width, height = 1160, 590
    x0, x1, y0, y1 = 105, 1040, 112, 485
    xmin = min(0, min(r[1] for r in rows)) - 1
    xmax = max(0, max(r[1] for r in rows)) + 1
    xp = lambda n: x0 + (n - xmin) * (x1 - x0) / (xmax - xmin)
    yp = lambda n: y1 - (n + 1) * (y1 - y0) / 2
    body = [text(36, 38, "C  ·  Cohort atlas", size=23, weight=500),
            text(36, 64, "All 80 matched sealed tasks: change in write calls versus change in final partial credit.", size=13, color=MUTED)]
    for delta in (-1, -0.5, 0, 0.5, 1):
        y = yp(delta)
        body += [line(x0, y, x1, y, color=INK if delta == 0 else GRID),
                 text(x0 - 13, y + 4, f'{delta:+.1f}', size=12, color=MUTED, anchor="end")]
    for delta in range(math.ceil(xmin / 5) * 5, xmax + 1, 5):
        x = xp(delta)
        body += [line(x, y0, x, y1, color=INK if delta == 0 else GRID),
                 text(x, y1 + 22, f'{delta:+d}', size=12, color=MUTED, anchor="middle")]
    body += [line(x0, y0, x0, y1), line(x0, y1, x1, y1)]
    # Duplicate coordinates occur often; a small deterministic offset reveals overlap.
    duplicate: dict[tuple[int, float, str], int] = {}
    for task_id, dw, dc in sorted(rows):
        key = (dw, round(dc, 5), task_id.split(":")[0])
        occurrence = duplicate.get(key, 0)
        duplicate[key] = occurrence + 1
        x = xp(dw) + (occurrence % 5 - 2) * 4
        y = min(y1 - 4, max(y0 + 4, yp(dc) + (occurrence // 5) * 4))
        color = AFTER_COLOR if task_id.startswith("finance") else WRITE
        if task_id in selected:
            body += [circle(x, y, 8, fill="white", stroke=INK), circle(x, y, 5, fill=color)]
        else:
            body += [circle(x, y, 4.4, fill=color)]
    for task_id, dx, dy in rows:
        if task_id not in selected:
            continue
        x, y = xp(dx), yp(dy)
        offset = 12 if task_id != "hr:5106" else -12
        body += [text(x + 13, y + offset, task_id, size=12, color=INK)]
    body += [text((x0 + x1) / 2, 548, "Change in write calls (after − before) →", size=14,
                  anchor="middle"), text(36, 109, "Δ credit ↑", size=13, color=MUTED),
             circle(917, 39, 5, fill=AFTER_COLOR), text(929, 44, "Finance", size=12),
             circle(1006, 39, 5, fill=WRITE), text(1018, 44, "HR", size=12)]
    return svg(width, height, "Cohort atlas of all 80 paired tasks", body)


def version_id(rules: list[str]) -> str:
    return "v0" if not rules else "s" + hashlib.sha256("\n".join(rules).encode()).hexdigest()[:8]


def edited_rules(rules: list[str], edit: dict) -> list[str]:
    result = list(rules)
    index = (edit.get("index") or 0) - 1
    if edit["op"] == "add":
        result.append(edit["text"].strip())
    elif edit["op"] == "replace":
        result[index] = edit["text"].strip()
    elif edit["op"] == "remove":
        result.pop(index)
    return result


def gate_runs(logs: Path, version: str) -> dict[str, dict]:
    return read_runs(logs / f"minimax-p1-{version}-cp-bench.jsonl")


def mean_credit(runs: dict[str, dict]) -> float:
    return sum(run["partial_credit"] for run in runs.values()) / len(runs)


def learning_ribbons(stages: list[dict[str, dict]]) -> str:
    # These three examples test the "ideal size" intuition: expansion,
    # compression, and a non-monotone individual result.
    examples = [
        ("hr:5079", "expands into the required writes"),
        ("hr:5093", "shortens while reaching full credit"),
        ("hr:5044", "improves, then regresses"),
    ]
    width, height = 1280, 710
    columns = [180, 535, 890]
    bar_width = 306
    body = [text(36, 38, "Ribbons through retained playbook versions", size=23, weight=500),
            text(36, 65, "The same gate task is rerun under each retained policy. The checkpoint stays on.",
                 size=13, color=MUTED)]
    for label, color, x in [("Search", SEARCH, 36), ("Read", READ, 128),
                            ("Write", WRITE, 208), ("Other", MUTED, 290)]:
        body += [rect(x, 83, 14, 14, fill=color), text(x + 20, 95, label, size=12)]
    body += [circle(379, 90, 6, fill="white", stroke=ERROR), text(393, 95, "Error", size=12)]
    headings = [
        ("Start", "No learned rule"),
        ("After round 1", "Finish every required write"),
        ("After round 2", "Read policy before writing"),
    ]
    for stage, (x, (label, detail)) in enumerate(zip(columns, headings)):
        runs = stages[stage]
        body += [text(x, 132, label, size=17, weight=500),
                 text(x, 151, detail, size=12, color=MUTED),
                 text(x, 173, f'Gate: {mean_credit(runs):.3f} credit · {sum(r["passed"] for r in runs.values())}/60 passes',
                      size=12, color=AFTER_COLOR)]
    for row, (task_id, note) in enumerate(examples):
        y = 203 + row * 137
        body += [text(36, y + 6, task_id, size=16, weight=500),
                 text(36, y + 25, note, size=12, color=MUTED)]
        max_calls = max(len(stage[task_id]["calls"]) for stage in stages)
        unit = bar_width / max_calls
        for stage, x in zip(stages, columns):
            run = stage[task_id]
            for i, call in enumerate(run["calls"]):
                mark_x = x + i * unit
                fill = {"search": SEARCH, "read": READ, "write": WRITE}.get(kind(call), MUTED)
                body += [rect(mark_x, y + 38, max(1.5, unit - 0.7), 22, fill=fill)]
                if failed(call):
                    body += [circle(mark_x + unit / 2, y + 49, 3.6, fill="white", stroke=ERROR)]
            write_count = counts(run)["write"]
            body += [text(x, y + 81,
                          f'{grade(run)} · {len(run["calls"])} calls · {write_count} writes',
                          size=12, color=INK)]
        body += [line(36, y + 106, 1244, y + 106)]
    body += [text(36, 651, "Rounds 3 and 4 evaluated new rules but retained no change; their policy ribbon remains the round-2 version.",
                  size=13, color=INK),
             text(36, 677, "Fixed 60-task gate; one stochastic run per task and version. Sealed exam contains only start and final versions.",
                  size=13, color=MUTED)]
    return svg(width, height, "Action ribbons through three retained playbook versions", body)


def policy_search(logs: Path, history: list[dict], retained: list[dict[str, dict]]) -> str:
    width, height = 1280, 500
    x_at = [145, 390, 635, 880, 1125]
    y0, y1 = 105, 365
    y_at = lambda score: y1 - (score - 0.58) * (y1 - y0) / (0.82 - 0.58)
    body = [text(36, 38, "Policy search: retained path and unselected trials", size=23, weight=500),
            text(36, 65, "Mean credit on the same 60 gate tasks at each evaluation; branch points are proposed rules.",
                 size=13, color=MUTED)]
    for score in (0.60, 0.65, 0.70, 0.75, 0.80):
        y = y_at(score)
        body += [line(100, y, 1190, y), text(90, y + 4, f'{score:.2f}', size=12,
                                            color=MUTED, anchor="end")]
    scores = [mean_credit(retained[0]), mean_credit(retained[1]), mean_credit(retained[2])]
    trunk = [scores[0], scores[1], scores[2], scores[2], scores[2]]
    for rnd, row in enumerate(history, 1):
        parent = trunk[rnd - 1]
        for decision in row["decisions"]:
            version = version_id(edited_rules(row["rules_before"], decision["edit"]))
            candidate = gate_runs(logs, version)
            value = mean_credit(candidate)
            if value > 0.82 or value < 0.58:
                raise ValueError(f"candidate score {value} outside plot scale")
            selected = row["kept"] == decision["edit"]
            body += [line(x_at[rnd - 1], y_at(parent), x_at[rnd], y_at(value),
                          color=AFTER_COLOR if selected else GRID, width=2 if selected else 1.5),
                     circle(x_at[rnd], y_at(value), 6 if selected else 5,
                            fill=AFTER_COLOR if selected else "white",
                            stroke=AFTER_COLOR if selected else BEFORE_COLOR)]
            if not selected:
                label_offset = 17 if rnd == 3 and value < trunk[rnd] else (-20 if rnd == 3 else -8)
                body += [text(x_at[rnd] + 12, y_at(value) + label_offset,
                              f'{value:.3f}', size=12, color=MUTED)]
    for rnd in range(4):
        body += [line(x_at[rnd], y_at(trunk[rnd]), x_at[rnd + 1], y_at(trunk[rnd + 1]),
                      color=AFTER_COLOR, width=3)]
    for rnd, value in enumerate(trunk):
        body += [circle(x_at[rnd], y_at(value), 7, fill=AFTER_COLOR),
                 text(x_at[rnd], y_at(value) - 13, f'{value:.3f}', size=12,
                      color=AFTER_COLOR, anchor="middle"),
                 text(x_at[rnd], 399, "Start" if rnd == 0 else f'Round {rnd}',
                      size=13, anchor="middle")]
    body += [circle(102, 434, 5, fill=AFTER_COLOR), text(114, 439, "retained playbook", size=12),
             circle(294, 434, 5, fill="white", stroke=BEFORE_COLOR),
             text(306, 439, "evaluated, not retained", size=12),
             text(36, 474, "A round-3 trial reached 0.791 mean credit but missed the +0.020 net-gain gate (+0.0135).",
                  size=13, color=MUTED)]
    return svg(width, height, "Policy search across four learning rounds", body)


def trajectory_dataset(before: dict, after: dict) -> list[dict]:
    """Export only categories and scores for the offline, all-task atlas."""
    if set(before) != set(after):
        raise ValueError("The sealed runs must contain identical task IDs")

    def compact(run: dict) -> dict:
        return {
            "credit": round(run["partial_credit"], 8),
            "passed": bool(run["passed"]),
            "holds": run["holds"],
            "actions": "".join(kind(call)[0].upper() if failed(call) else kind(call)[0]
                             for call in run["calls"]),
        }

    return [{"id": task_id, "domain": task_id.split(":", 1)[0],
             "before": compact(before[task_id]), "after": compact(after[task_id])}
            for task_id in sorted(before)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True, help="phase1_run log directory")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    before = read_runs(args.logs / BEFORE)
    after = read_runs(args.logs / AFTER)
    if len(before.keys() & after.keys()) != 80:
        raise SystemExit(f"Expected 80 paired tasks, got {len(before.keys() & after.keys())}")
    args.output.mkdir(parents=True, exist_ok=True)
    history = json.loads((ROOT / "v2/phase1/run/take2/skill_history.json").read_text(encoding="utf-8"))
    versions = [version_id(history[0]["rules_before"]),
                version_id(history[0]["rules_after"]),
                version_id(history[1]["rules_after"])]
    stages = [gate_runs(args.logs, version) for version in versions]
    if len(set.intersection(*(set(stage) for stage in stages))) != 60:
        raise SystemExit("Expected the same 60 gate tasks across retained versions")
    for filename, artwork in [
        ("action-ribbons.svg", ribbons(before, after)),
        ("action-space-portraits.svg", portraits(before, after)),
        ("cohort-atlas.svg", atlas(before, after)),
        ("learning-ribbons.svg", learning_ribbons(stages)),
        ("policy-search.svg", policy_search(args.logs, history, stages)),
    ]:
        (args.output / filename).write_text(artwork, encoding="utf-8")
        print(args.output / filename)
    data_path = args.output / "trajectories-data.js"
    data_path.write_text("window.TRAJECTORIES = " + json.dumps(
        trajectory_dataset(before, after), separators=(",", ":")) + ";\n", encoding="utf-8")
    print(data_path)


if __name__ == "__main__":
    main()
