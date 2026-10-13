"""Draw the headline figure (docs/img/headline.svg) from the committed per-run table. Standard library only.

    python3 scripts/make_headline_figure.py
"""
import csv
import statistics as st
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
OUT = V2.parent / "docs" / "img" / "headline.svg"


def main() -> None:
    arms: dict[str, list[dict]] = {}
    with open(V2 / "phase1" / "run" / "take2" / "sealed_runs.csv", newline="") as f:
        for r in csv.DictReader(f):
            arms.setdefault(r["arm"], []).append(r)
    final = {r["task_id"]: r for r in arms["final_playbook_checkpoint_on"]}
    redo = {r["task_id"]: r for r in arms["gemini_redo_for_escalated"]}
    credit = lambda rs: st.mean(float(r["partial_credit"]) for r in rs)
    cost = lambda rs: st.mean(float(r["cost_usd"]) for r in rs)
    router_credit = st.mean(float((redo.get(t) or final[t])["partial_credit"]) for t in final)
    router_cost = st.mean(float(final[t]["cost_usd"]) + 0.002 + (float(redo[t]["cost_usd"]) if t in redo else 0.0)
                          for t in final)
    rows = [
        ("Open-weight model, before", credit(arms["starting_playbook_checkpoint_on"]),
         cost(arms["starting_playbook_checkpoint_on"]), "#8a94a6"),
        ("Same model, after the harness", credit(final.values()), cost(final.values()), "#2f6fed"),
        ("Router: that model, Gemini on 45% of tasks", router_credit, router_cost, "#12a594"),
        ("Gemini 3.8 Flash alone", credit(arms["gemini_alone"]), cost(arms["gemini_alone"]), "#3b4252"),
    ]
    W, left, bar_max, row_h, top = 860, 300, 330, 54, 62
    H = top + row_h * len(rows) + 62
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f'<rect width="{W}" height="{H}" rx="12" fill="#ffffff"/>',
         f'<text x="24" y="34" font-size="17" font-weight="700" fill="#1b2230">'
         f'Credit on 80 unseen back-office tasks (sealed exam, one run each)</text>',
         f'<text x="{left + bar_max + 28}" y="{top - 12}" font-size="12" fill="#5b6475">cost per task</text>']
    for i, (label, c, k, color) in enumerate(rows):
        y = top + i * row_h
        s += [f'<text x="24" y="{y + 24}" font-size="14" fill="#1b2230">{label}</text>',
              f'<rect x="{left}" y="{y + 6}" width="{bar_max}" height="26" rx="5" fill="#eef1f6"/>',
              f'<rect x="{left}" y="{y + 6}" width="{c * bar_max:.1f}" height="26" rx="5" fill="{color}"/>',
              f'<text x="{left + c * bar_max - 10:.1f}" y="{y + 24}" font-size="14" font-weight="700" fill="#ffffff" '
              f'text-anchor="end">{c:.3f}</text>',
              f'<text x="{left + bar_max + 28}" y="{y + 25}" font-size="15" font-weight="600" fill="#1b2230">${k:.3f}</text>']
    s += [f'<text x="24" y="{H - 34}" font-size="12" fill="#5b6475">Credit = the share of each task\'s record '
          f'checks that end up right.</text>',
          f'<text x="24" y="{H - 16}" font-size="12" fill="#5b6475">Source: v2/phase1/run/take2/sealed_runs.csv'
          f"  \u00b7  re-derive: python3 v2/scripts/rederive_sealed.py</text>",
          '</svg>']
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(s) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
