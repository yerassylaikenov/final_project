#!/usr/bin/env bash
# One experiment run in Kubernetes:  ./experiment.sh off | on
# 0 s load starts, 30 s dep-a breaks (FAULT), 60 s dep-a repaired, 120 s load ends.
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-off}"
DEFAULT_FAULT='{"unavailable": true}'               # variant 5: dep-a unavailable (503)
FAULT="${FAULT:-$DEFAULT_FAULT}"
NAME="${NAME:-k8s_$MODE}"
EXTRA_ENV="${EXTRA_ENV:-}"                          # e.g. EXTRA_ENV="PLAN_MAX_AGE_S=10"
if python3 -c "" 2>/dev/null; then PY=python3; else PY=python; fi
mkdir -p results

log() { echo "[experiment $(date +%H:%M:%S)] $*"; }

set_fault() {
  kubectl exec deploy/dep-a -- python -c "import urllib.request as u; \
u.urlopen(u.Request('http://127.0.0.1:8081/fault', data=b'$1', method='POST', \
headers={'Content-Type': 'application/json'})).read()" >/dev/null
}

log "mode PATTERN=$MODE, FAULT=$FAULT ${EXTRA_ENV}"
set_fault '{}'
kubectl set env deployment/core PATTERN="$MODE" PLAN_MAX_AGE_S- >/dev/null
if [ -n "$EXTRA_ENV" ]; then kubectl set env deployment/core $EXTRA_ENV >/dev/null; fi
kubectl rollout status deployment/core --timeout=180s >/dev/null
log "core rolled out with PATTERN=$MODE"
kubectl get pods -l app=core | grep -v Terminating || true

kubectl delete job loadgen --ignore-not-found >/dev/null
# use the cluster clock (it can differ from this machine, e.g. Docker Desktop VM)
OFFSET=$(( $(kubectl exec deploy/dep-a -- python -c "import time; print(int(time.time()))") - $(date +%s) ))
START_AT=$(( $(date +%s) + OFFSET + 20 ))           # load starts at this exact second
sed "s/name: START_AT, value: \"0\"/name: START_AT, value: \"$START_AT\"/" load-job.yaml | kubectl apply -f - >/dev/null
kubectl wait --for=condition=ready pod -l job-name=loadgen --timeout=180s >/dev/null

wait_until() { while [ $(( $(date +%s) + OFFSET )) -lt "$1" ]; do sleep 0.2; done; }
wait_until "$START_AT"
log "t=0s   loadgen started (20 rps, client timeout 1.5 s)"
wait_until $(( START_AT + 30 ))
set_fault "$FAULT"
log "t=30s  dep-a BROKEN: $FAULT"
wait_until $(( START_AT + 60 ))
set_fault '{}'
log "t=60s  dep-a REPAIRED"

kubectl wait --for=condition=complete job/loadgen --timeout=180s >/dev/null
kubectl logs job/loadgen > "results/$NAME.csv"
kubectl logs -l app=core --tail=-1 --prefix > "results/$NAME.log" 2>&1 || true
log "t=120s loadgen finished, saved results/$NAME.csv"
$PY metrics.py "results/$NAME.csv" --json "results/metrics_$NAME.json"
