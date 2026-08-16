#!/usr/bin/env bash
# Run the full BVCRSA experiment suite unattended on AWS EC2.
#
#   tmux new -s bvcrsa
#   bash AWS/run_all.sh
#   Ctrl-B then D          <- detach; close your laptop, go to class
#   tmux attach -t bvcrsa  <- reattach from anywhere, any machine
#
# Every experiment writes its own log to logs/. If one fails the rest still
# run, so a single broken experiment does not cost you the whole night.

set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
LOGS="$ROOT/logs"
mkdir -p "$LOGS"

# The experiments print box-drawing characters and emoji. When stdout is a
# pipe or a file rather than a terminal, Python picks its encoding from the
# locale -- and a non-interactive SSH session on Ubuntu often has LANG unset,
# giving ASCII. Every print() then dies with UnicodeEncodeError, hours into
# an unattended run. Force UTF-8 so redirecting to logs/ is safe.
export PYTHONIOENCODING=utf-8
export LC_ALL="${LC_ALL:-C.UTF-8}"
export LANG="${LANG:-C.UTF-8}"

if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ -f "$HOME/venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        . "$HOME/venv/bin/activate"
    else
        echo "!! No virtualenv active and ~/venv not found."
        echo "   python3 -m venv ~/venv && . ~/venv/bin/activate"
        echo "   pip install numpy matplotlib pycryptodome py_ecc ecdsa pandas py_arkworks_bls12381"
        exit 1
    fi
fi

echo "=============================================================="
echo "  BVCRSA suite"
echo "  started : $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
echo "  python  : $(python --version 2>&1)"
echo "  host    : $(hostname)"
echo "  logs    : $LOGS"
echo "=============================================================="

STARTED=$(date +%s)

run () {                       # run <dir> <script> <label>
    local dir="$1" script="$2" label="$3"
    local log="$LOGS/${label}.log"
    printf '\n>>> %-26s ' "$label"
    local t0; t0=$(date +%s)
    if ( cd "Benchmark/$dir" && python "$script" ) >"$log" 2>&1; then
        local t1; t1=$(date +%s)
        printf 'OK    %6ss   -> %s\n' "$((t1 - t0))" "${log#$ROOT/}"
    else
        local t1; t1=$(date +%s)
        printf 'FAIL  %6ss   -> %s\n' "$((t1 - t0))" "${log#$ROOT/}"
        printf '    last lines:\n'
        tail -n 4 "$log" | sed 's/^/      /'
    fi
}

# ── Sanity first. If this fails, nothing downstream is trustworthy. ──
printf '\n>>> %-26s ' "test_pipeline"
if ( cd Benchmark/_shared && python test_pipeline.py ) >"$LOGS/00_test_pipeline.log" 2>&1; then
    echo "OK"
else
    echo "FAIL -- aborting."
    tail -n 15 "$LOGS/00_test_pipeline.log" | sed 's/^/    /'
    exit 1
fi

# ── Calibration. Run before the rest: it gives the expected cost of
#    every other experiment, so an implausible result is caught early. ──
run 10_Primitive_Microbench   experiment.py       10_microbench

# ── Short experiments ──
run 01_Trapdoor_Gen           experiment.py       01_trapdoor
run 07_Aggregate_Recovery_BSGS experiment.py      07_bsgs
run 08_Communication_Cost     experiment.py       08_communication

# ── Medium ──
run 04_Verification_Overhead  experiment.py       04_verification
run 04_Verification_Overhead  plot.py             04_verification_plot
run 05_Homomorphic_Aggregation experiment.py      05_aggregation

# ── Long. Leave these running overnight. ──
run 06_Aggregation_Strategy   experiment.py       06_agg_strategy
run 06_Aggregation_Strategy   experiment_zoom.py  06_agg_strategy_zoom
run 06_Aggregation_Strategy   plot.py             06_agg_strategy_plot
run 03_Query_Throughput       experiment.py       03_throughput
run 02_Query_Processing       experiment.py       02_query_processing

# Exp 09 needs a Raspberry Pi; Exp 11 needs a multi-node Ethereum cluster.
# Neither is run here -- see their config.md.

ELAPSED=$(( $(date +%s) - STARTED ))
echo ""
echo "=============================================================="
printf '  finished : %s\n' "$(date -u +'%Y-%m-%d %H:%M:%S UTC')"
printf '  elapsed  : %dh %dm\n' "$((ELAPSED / 3600))" "$(((ELAPSED % 3600) / 60))"
echo "--------------------------------------------------------------"
echo "  CSV written:"
ls -1 CSV/exp*.csv 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo "  Figures written:"
ls -1 Figures/*.svg 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo "=============================================================="
echo ""
echo "Pull the results down from your own machine:"
echo "  rsync -avz -e 'ssh -i <key>.pem' ubuntu@<ip>:~/bvcrsa/CSV/     ./CSV/"
echo "  rsync -avz -e 'ssh -i <key>.pem' ubuntu@<ip>:~/bvcrsa/Figures/ ./Figures/"
echo "  rsync -avz -e 'ssh -i <key>.pem' ubuntu@<ip>:~/bvcrsa/logs/    ./logs/"
echo ""
echo "Then STOP the instance so it stops costing money."
