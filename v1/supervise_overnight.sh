#!/bin/zsh
# Unattended driver for the rest of experiments 2 and 3.
#
#   1. Experiment 2 learning: wait for the running launch; if it ends without frozen
#      versions, relaunch (everything finished replays from cache).
#   2. Experiment 2 sealed stage, then 3. experiment 3 sealed stage (fresh set).
#
# Transient failures (rate limits, network, provider hiccups) are retried up to
# MAX_ATTEMPTS per stage. Fatal ones stop everything: out of credit, served model or
# provider changed, spend cap reached. Log: logs/supervisor.log
set -u
MAIN=~/Documents/jev-test-poc
EXP3=~/Documents/jev-test-poc-exp3
LOG=$MAIN/logs/supervisor.log
MAX_ATTEMPTS=6
FATAL='OutOfCreditsError|RouteMismatchError|SpendCapExceeded'
mkdir -p $MAIN/logs
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a $LOG; }

fatal_in() { grep -qE "$FATAL" "$1" 2>/dev/null; }

# run_stage NAME DIR DONE_FILE CMD_PREFIX RUN_ID_BASE STDOUT_DIR
run_stage() {
  local name=$1 dir=$2 done_file=$3 cmd=$4 base=$5 outdir=$6 wait_pattern=""
  cd $dir
  if [ -n "$wait_pattern" ]; then
    while pgrep -f "$wait_pattern" >/dev/null; do sleep 30; done
  fi
  local attempt=0 out
  while [ ! -f "$done_file" ]; do
    attempt=$((attempt + 1))
    if [ $attempt -gt $MAX_ATTEMPTS ]; then
      say "STOP: $name did not finish after $MAX_ATTEMPTS attempts"; exit 1
    fi
    local run_id="${base}-s${attempt}"
    out="$outdir/${run_id}.stdout"
    say "$name: attempt $attempt ($run_id)"
    eval "$cmd --run-id $run_id" > "$out" 2>&1
    if [ -f "$done_file" ]; then break; fi
    if fatal_in "$out"; then
      say "STOP (fatal): $name — $(grep -oE "$FATAL[^\"]{0,160}" "$out" | head -1)"; exit 2
    fi
    say "$name: attempt $attempt ended without output ($(tail -1 "$out" | cut -c1-160)); retrying in 60 s"
    sleep 60
  done
  say "$name: done"
}

say "supervisor started"
# Stage 1 waits for the launch already running, then relaunches only if needed.
if [ ! -f $MAIN/results/arena/final_versions.json ]; then
  cd $MAIN
  while pgrep -f "learn.py --run-id arena-learn-20260926" >/dev/null; do sleep 30; done
fi
run_stage "exp2 learning" $MAIN $MAIN/results/arena/final_versions.json \
  ".venv/bin/python -u learn.py" "arena-learn-20260926-sup" $MAIN/logs/arena
run_stage "exp2 sealed" $MAIN $MAIN/results/arena/sealed_complete.json \
  ".venv/bin/python -u sealed.py" "arena-sealed-20260926" $MAIN/logs/arena
run_stage "exp3 sealed" $EXP3 $EXP3/results/arena3/sealed_complete.json \
  ".venv/bin/python -u sealed_trace.py" "arena3-sealed-20260926" $EXP3/logs/arena3
say "ALL DONE: experiment 2 and 3 verdicts written"
