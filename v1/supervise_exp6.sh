#!/bin/zsh
# Unattended driver for experiment 6: learning, then the single sealed stage.
# Transient failures are retried (finished calls replay from cache); fatal ones stop:
# out of credit, served model/provider changed, spend cap reached. Log: logs/supervisor6.log
set -u
MAIN=~/Documents/jev-test-poc
LOG=$MAIN/logs/supervisor6.log
MAX_ATTEMPTS=6
FATAL='OutOfCreditsError|RouteMismatchError|SpendCapExceeded'
mkdir -p $MAIN/logs/upworthy6
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a $LOG; }
cd $MAIN
run_stage() {
  local name=$1 stage=$2 done_file=$3 base=$4 attempt=0 out
  while [ ! -f "$done_file" ]; do
    attempt=$((attempt + 1))
    if [ $attempt -gt $MAX_ATTEMPTS ]; then say "STOP: $name did not finish after $MAX_ATTEMPTS attempts"; exit 1; fi
    out="$MAIN/logs/upworthy6/${base}-s${attempt}.stdout"
    say "$name: attempt $attempt (${base}-s${attempt})"
    .venv/bin/python -u learn_bandit.py --stage $stage --run-id "${base}-s${attempt}" > "$out" 2>&1
    [ -f "$done_file" ] && break
    if grep -qE "$FATAL" "$out"; then say "STOP (fatal): $name — $(grep -oE "($FATAL)[^\"]{0,160}" "$out" | head -1)"; exit 2; fi
    say "$name: attempt $attempt ended without output ($(tail -1 "$out" | cut -c1-160)); retrying in 60 s"
    sleep 60
  done
  say "$name: done"
}
say "supervisor started"
run_stage "exp6 learning" learn $MAIN/results/upworthy6/final_versions.json upworthy6-learn-20260927
run_stage "exp6 sealed" sealed $MAIN/results/upworthy6/sealed_complete.json upworthy6-sealed-20260927
say "ALL DONE: experiment 6 verdict written"
