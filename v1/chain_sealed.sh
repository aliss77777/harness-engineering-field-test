#!/bin/zsh
# Waits for experiment 2's learning to finish, then runs experiment 2's sealed stage,
# then experiment 3's. Each step runs only if the previous one produced its output.
set -u
MAIN=~/Documents/jev-test-poc
EXP3=~/Documents/jev-test-poc-exp3
LEARN_ID=${1:?learning run id}
cd $MAIN
while pgrep -f "learn.py --run-id $LEARN_ID" >/dev/null; do sleep 30; done
if [ ! -f results/arena/final_versions.json ]; then
  echo "$(date) CHAIN STOPPED: experiment 2 learning ended without frozen versions"; exit 1
fi
echo "$(date) CHAIN: experiment 2 learning frozen; starting experiment 2 sealed"
.venv/bin/python -u sealed.py --run-id arena-sealed-20260926 > logs/arena/arena-sealed-20260926.stdout 2>&1
if [ ! -f results/arena/sealed_complete.json ]; then
  echo "$(date) CHAIN STOPPED: experiment 2 sealed did not complete"; exit 1
fi
echo "$(date) CHAIN: experiment 2 verdict written; starting experiment 3 sealed"
cd $EXP3
.venv/bin/python -u sealed_trace.py --run-id arena3-sealed-20260926 > logs/arena3/arena3-sealed-20260926.stdout 2>&1
if [ ! -f results/arena3/sealed_complete.json ]; then
  echo "$(date) CHAIN STOPPED: experiment 3 sealed did not complete"; exit 1
fi
echo "$(date) CHAIN DONE: both verdicts written"
