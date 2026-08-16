#!/usr/bin/env bash
# Pull results from the three AWS workers into the project tree.
#
#   bash AWS/collect.sh [path-to-key.pem]
#
# Safe to run repeatedly, and while the workers are still going -- you just
# get whatever has landed so far.

set -u
cd "$(dirname "$0")/.." || exit 1

KEY="${1:-$HOME/BVCRSA_key.pem}"
[ -f "$KEY" ] || KEY="/c/Users/Jzguyr/Downloads/BVCRSA_key.pem"
if [ ! -f "$KEY" ]; then
    echo "!! key not found. Pass it explicitly:  bash AWS/collect.sh ~/BVCRSA_key.pem"
    exit 1
fi

W1=44.197.171.184
W2=98.92.182.127
W3=34.206.1.190

mkdir -p CSV Figures logs

SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=20"

echo "=============================================================="
echo "  Collecting BVCRSA results"
echo "=============================================================="

# --- status first, so you know whether it is finished -------------
for pair in "W1:$W1" "W2:$W2" "W3:$W3"; do
    L="${pair%%:*}"; IP="${pair##*:}"
    printf '\n--- %s (%s) ---\n' "$L" "$IP"
    $SSH ubuntu@"$IP" "tail -n 20 ~/bvcrsa/logs/STATUS_${L}.txt 2>/dev/null || echo '  (no status yet)'"
done

echo ""
echo "--------------------------------------------------------------"
echo "  Pulling artifacts"
echo "--------------------------------------------------------------"

pull () {   # pull <ip> <remote-subdir> <local-dir>
    if command -v rsync >/dev/null 2>&1; then
        rsync -az -e "$SSH" "ubuntu@$1:~/bvcrsa/$2/" "./$3/" 2>/dev/null
    else
        scp -q -i "$KEY" -o StrictHostKeyChecking=no \
            "ubuntu@$1:~/bvcrsa/$2/*" "./$3/" 2>/dev/null
    fi
}

for pair in "W1:$W1" "W2:$W2" "W3:$W3"; do
    L="${pair%%:*}"; IP="${pair##*:}"
    echo "  $L ..."
    # Each worker ran its own Exp 10; keep them separate so every result set
    # can be reconciled against ITS OWN primitive costs (R2-C3).
    scp -q -i "$KEY" -o StrictHostKeyChecking=no \
        "ubuntu@$IP:~/bvcrsa/CSV/exp10_primitive_microbench.csv" \
        "./CSV/exp10_primitive_microbench__${L}.csv" 2>/dev/null
    pull "$IP" CSV CSV
    pull "$IP" Figures Figures
    pull "$IP" logs logs
done

# The shared-name Exp 10 copy is ambiguous once merged -- drop it, the
# per-worker copies above are the authoritative ones.
rm -f CSV/exp10_primitive_microbench.csv

echo ""
echo "=============================================================="
echo "  CSV:"
ls -1 CSV/exp*.csv 2>/dev/null | sed 's/^/    /' || echo "    (none yet)"
echo "  Figures:"
ls -1 Figures/*.svg 2>/dev/null | sed 's/^/    /' || echo "    (none yet)"
echo "=============================================================="
echo ""
echo "When every worker shows WORKER_*_COMPLETE, stop the instances."
echo "Then convert figures for Overleaf:"
echo "  for f in Figures/*.svg; do inkscape \"\$f\" --export-type=pdf \\"
echo "      --export-filename=\"\${f%.svg}.pdf\"; done"
