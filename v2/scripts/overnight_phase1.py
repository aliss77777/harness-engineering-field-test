"""Unattended run of Take 2's remaining learning stages (Alexander, 2026-10-10).

    caffeinate -i .venv/bin/python -u scripts/overnight_phase1.py

Order: wait for the replay of length-refused rules to finish (re-running it if it stopped) -> adopt its
winner only if the reading rule is met -> jevdata -> rubric -> tau. It NEVER runs the sealed exam (that needs
Alexander's written release) and stops at the first failure. Before each paid stage it checks the OpenRouter
balance and waits, rather than failing with a 402 halfway through, if the balance is too low.

Reading rule for adopting a replay winner (fixed 2026-10-10, before results): it passed the margin keep test,
its test bench credit is at least +0.07 above the baseline, and its fully passed tasks are not lower. At most
one rule is adopted (the largest credit gain); otherwise the playbook stays as it is.
"""
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jevloop.skill_loop import version_id  # noqa: E402

PY = str(ROOT / ".venv" / "bin" / "python")
RUN = str(ROOT / "scripts" / "phase1_run.py")
OUT = ROOT / "phase1" / "run" / "take2"
LOG = ROOT / "logs" / "phase1_run" / "overnight.log"
MIN_CREDIT_GAIN = 0.07  # reading rule: a clear test bench signal
STAGE_ESTIMATE_USD = {"replay-refused": 4.5, "jevdata": 3.5, "rubric": 1.0, "tau": 0.5}  # remaining need, with some margin; waits if the balance is below this + $0.5
CHECK_EVERY_S, MAX_WAIT_S = 300, 10 * 3600
MIN_FLOAT_USD = 1.0  # proceed with at least this much usable balance. Auto top-up fires at $2 as credit is spent, so a higher bar could wait forever at $2-3; a stage that stops on credit is retried


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_KEY missing")


def balance_usd() -> float | None:
    """What this key can still spend: the account's credit balance, capped by the key's own limit if it has one
    (a key limit of its own stops calls with a 403 even when the account has credit and auto top-up is on)."""
    try:
        headers = {"Authorization": f"Bearer {api_key()}"}
        d = httpx.get("https://openrouter.ai/api/v1/credits", headers=headers, timeout=20).json()["data"]
        bal = float(d["total_credits"]) - float(d["total_usage"])
        k = httpx.get("https://openrouter.ai/api/v1/key", headers=headers, timeout=20).json().get("data", {})
        if k.get("limit_remaining") is not None:
            bal = min(bal, float(k["limit_remaining"]))
        return bal
    except Exception as error:  # noqa: BLE001
        log(f"balance check failed ({type(error).__name__}); continuing")
        return None


def wait_for_credit(stage: str) -> None:
    # Auto top-up only fires as credit is used, so ask for a working float, not the whole stage's estimate.
    need = min(STAGE_ESTIMATE_USD[stage] + 0.5, MIN_FLOAT_USD)
    waited = 0
    while True:
        bal = balance_usd()
        if bal is None or bal >= need:
            log(f"{stage}: OpenRouter balance ${bal:.2f} (need about ${need:.2f})" if bal is not None else f"{stage}: balance unknown")
            return
        if waited >= MAX_WAIT_S:
            log(f"{stage}: gave up waiting for credit (balance ${bal:.2f}, need ${need:.2f})")
            sys.exit(2)
        log(f"{stage}: balance ${bal:.2f} is below ${need:.2f}; waiting for a top-up (check every {CHECK_EVERY_S // 60} min)")
        time.sleep(CHECK_EVERY_S)
        waited += CHECK_EVERY_S


def replay_running() -> bool:
    ps = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return any("phase1_run.py replay-refused" in line and "overnight_phase1" not in line for line in ps.splitlines())


def run_stage(stage: str) -> int:
    wait_for_credit(stage)
    log(f"START {stage}")
    with (ROOT / "logs" / "phase1_run" / f"overnight-{stage}.stdout").open("a") as out:
        rc = subprocess.run([PY, "-u", RUN, stage], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT).returncode
    log(f"END {stage} (exit {rc})")
    return rc


def decide(replay: dict) -> dict:
    """The reading rule applied to skill_replay.json. Returns {"adopt": bool, "edit": dict | None, "why": str}."""
    ok = []
    for r in replay["results"]:
        d = r["decision"]
        if d["keep"] and d["net_diff"] >= MIN_CREDIT_GAIN - 1e-9 and d["passes_diff"] >= 0:
            ok.append(r)
    if not ok:
        best = max(replay["results"], key=lambda r: r["decision"]["net_diff"], default=None)
        why = "no replay candidate cleared the reading rule" + (
            f" (best credit change {best['decision']['net_diff']:+.3f}, passes {best['decision']['passes_diff']:+d}, "
            f"{'passed' if best['decision']['keep'] else 'failed'} the margin test)" if best else "")
        return {"adopt": False, "edit": None, "why": why}
    win = max(ok, key=lambda r: r["decision"]["net_diff"])
    return {"adopt": True, "edit": win["edit"], "why": f"credit {win['decision']['net_diff']:+.3f}, passes {win['decision']['passes_diff']:+d}, "
                                                       f"targeted {win['decision']['targeted_diff']:+.3f}"}


def adopt(decision: dict) -> None:
    final_path = OUT / "skill_final.json"
    final = json.loads(final_path.read_text())
    shutil.copy(final_path, OUT / "skill_final_before_replay.json")
    rules = list(final["rules"]) + [decision["edit"]["text"].strip()]
    new = {**final, "rules": rules, "version": version_id(tuple(rules)),
           "adopted_from_replay": {"edit": decision["edit"], "why": decision["why"], "previous_version": final["version"]}}
    final_path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
    log(f"ADOPTED replay winner; playbook {final['version']} -> {new['version']} ({len(rules)} rules)")


def main() -> None:
    log("overnight driver started (never runs the sealed exam)")
    while replay_running():
        log("waiting for the running replay to finish")
        time.sleep(60)
    for attempt in range(4):
        if (OUT / "skill_replay.json").exists():
            break
        log(f"replay result missing; running replay-refused (attempt {attempt + 1}; finished runs are reloaded)")
        if run_stage("replay-refused") != 0:
            time.sleep(180)
    if not (OUT / "skill_replay.json").exists():
        log("STOP: replay did not produce skill_replay.json")
        sys.exit(1)
    decision = decide(json.loads((OUT / "skill_replay.json").read_text()))
    (OUT / "replay_decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    log(f"replay decision: adopt={decision['adopt']}: {decision['why']}")
    if decision["adopt"] and not (OUT / "skill_final_before_replay.json").exists():
        adopt(decision)
    for stage in ("jevdata", "rubric", "tau"):
        for attempt in range(3):  # a stage stopped by credit or a transient error resumes without repaying
            if run_stage(stage) == 0:
                break
            log(f"{stage} failed (attempt {attempt + 1} of 3); waiting 3 min, then retrying (finished runs are reloaded)")
            time.sleep(180)
        else:
            log(f"STOP: {stage} failed 3 times; later stages not run. See logs/phase1_run/overnight-{stage}.stdout")
            sys.exit(1)
    log("DONE: jevdata, rubric and tau finished. The sealed exam was NOT run (needs Alexander's release).")


if __name__ == "__main__":
    main()
