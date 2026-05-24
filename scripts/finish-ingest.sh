#!/bin/bash
# Master-Timeline-Chabad full ingest watcher.
#
# Drives the entire Pass 2 → Pass 5 sequence to completion, surviving
# rate-limit crashes by re-invoking `make pass2` (the per-chunk disk
# cache makes re-runs cheap; chunks already done aren't repeated).
# When `02_extracted.json` is present, chains pass3 → pass4 → pass5
# → commit of public/ artifacts.
#
# Designed to be launched detached and forgotten:
#   nohup bash scripts/finish-ingest.sh </dev/null >/dev/null 2>&1 &
#
# Logs to /tmp/finish-ingest.log. Tail that for status.

set -u   # don't `set -e`: we want to react to failures, not exit on them.

REPO=/home/chassidusaicon/code/master-timeline-chabad
INGEST=$REPO/ingest
LOG=/tmp/finish-ingest.log
EXTRACTED=$INGEST/intermediate/02_extracted.json
MAX_PASS2_RESTARTS=50         # tolerate a full overnight Max-window closure
PASS2_RESTART_DELAY_S=300     # base backoff between restarts (5 min)
PASS2_RESTART_DELAY_MAX_S=3600  # cap after exponential backoff (1 hour)

ts()  { date +"%Y-%m-%d %H:%M:%S"; }
log() { printf "[%s] %s\n" "$(ts)" "$*" >> "$LOG"; }

pass2_alive() {
  # Match only the actual Python invocation, not bash wrappers / monitor
  # scripts / heredocs whose command-line happens to contain that string.
  pgrep -fa "timeline_ingest pass2" 2>/dev/null \
    | grep -E "^[0-9]+ .*(python|/python3).*-m timeline_ingest pass2" \
    | grep -qv "$0" \
    || return 1
  return 0
}

cache_count() {
  ls "$INGEST/cache" 2>/dev/null | wc -l
}

log "=== finish-ingest watcher started (PID $$) ==="
log "cache count at start: $(cache_count)"

# -----------------------------------------------------------------------
# Phase 1: ensure 02_extracted.json gets written.
# -----------------------------------------------------------------------
restart_count=0
while [ ! -f "$EXTRACTED" ]; do
  if pass2_alive; then
    sleep 60
    continue
  fi

  # pass2 not running, output not present — needs (re)start.
  if [ "$restart_count" -ge "$MAX_PASS2_RESTARTS" ]; then
    log "ERROR: exhausted $MAX_PASS2_RESTARTS pass2 restart attempts; giving up"
    exit 1
  fi

  log "pass2 not running, 02_extracted.json missing — (re)starting pass2 (attempt $((restart_count + 1)))"
  log "  cache count before restart: $(cache_count)"
  cd "$INGEST" || { log "ERROR: cannot cd to $INGEST"; exit 2; }
  nohup uv run python -m timeline_ingest pass2 >> /tmp/pass2.log 2>&1 &
  PASS2_PID=$!
  log "  spawned pass2 PID=$PASS2_PID"
  restart_count=$((restart_count + 1))

  # Wait a tiny bit so the process has registered, then loop.
  sleep 5
  if ! pass2_alive; then
    # Exponential backoff so an overnight Max closure doesn't burn the
    # whole restart budget in a tight loop. Doubles each consecutive
    # instant-kill, capped at PASS2_RESTART_DELAY_MAX_S.
    exp=$(( restart_count - 1 ))
    if [ "$exp" -gt 5 ]; then exp=5; fi
    multiplier=1
    for (( j=0; j<exp; j++ )); do multiplier=$(( multiplier * 2 )); done
    delay=$(( PASS2_RESTART_DELAY_S * multiplier ))
    if [ "$delay" -gt "$PASS2_RESTART_DELAY_MAX_S" ]; then
      delay=$PASS2_RESTART_DELAY_MAX_S
    fi
    log "  pass2 died immediately after spawn — sleeping ${delay}s before next retry"
    sleep "$delay"
  fi
done

log "Phase 1 complete: $EXTRACTED present ($(stat -c%s "$EXTRACTED" 2>/dev/null) bytes)"
log "Pass 2 restart attempts used: $restart_count"

# -----------------------------------------------------------------------
# Phase 2: pass3 → pass4 → pass5 → commit. Each pass uses LLM cache, so
# a transient crash mid-pass is recoverable by re-running the same pass.
# -----------------------------------------------------------------------
cd "$INGEST" || { log "ERROR: cannot cd to $INGEST"; exit 3; }

run_pass() {
  local pass_name=$1
  local attempts=$2
  local i=0
  while [ "$i" -lt "$attempts" ]; do
    log "Starting $pass_name (attempt $((i + 1))/$attempts)…"
    if uv run python -m timeline_ingest "$pass_name" >> "$LOG" 2>&1; then
      log "$pass_name OK"
      return 0
    fi
    log "$pass_name failed (attempt $((i + 1))); sleeping ${PASS2_RESTART_DELAY_S}s"
    sleep "$PASS2_RESTART_DELAY_S"
    i=$((i + 1))
  done
  log "ERROR: $pass_name exhausted $attempts attempts"
  return 1
}

run_pass pass3 5 || exit 4
run_pass pass4 3 || exit 5

log "Generating review.html (non-fatal if it fails)…"
uv run python -m timeline_ingest review >> "$LOG" 2>&1 || log "  review generation failed (non-fatal)"

run_pass pass5 3 || exit 6

# -----------------------------------------------------------------------
# Phase 3: commit the artifacts.
# -----------------------------------------------------------------------
cd "$REPO" || { log "ERROR: cannot cd to $REPO"; exit 7; }
log "Staging public artifacts for commit…"
git add public/events.json public/stories/ public/photos/ >> "$LOG" 2>&1 || true

if git diff --cached --quiet; then
  log "Nothing to commit — public/ unchanged"
else
  RUNDATE=$(date +%Y-%m-%d)
  if git commit -m "data: ingest run $RUNDATE — full corpus emit" >> "$LOG" 2>&1; then
    log "committed: $(git rev-parse --short HEAD)"
  else
    log "WARN: commit failed — run \`git status\` to inspect"
  fi
fi

log "=== finish-ingest watcher complete ==="
