# shellcheck shell=bash
# Stage broker hookup for --stage PROJECT, sourced by run.sh (spec 0002 REQ-5).
#
# The box runs its project's compose stack through the host-side broker
# (dev-root tools/stage-broker), never through Docker: it drops requests in
# its own mailbox at /bus/.stage (STAGE_QUEUE). Which project a box may run
# comes from a registry entry the launcher writes outside the mailbox, keyed
# by the bus key, so the box can neither see nor change it.
#
# One live box per key. A live stage box holds an exclusive flock on
# ~/.cache/claude-docker/locks/stage-<key>.lock for as long as its launcher
# runs (fd 8, inherited by docker run); any running container labelled
# claude-docker.bus-key=<key> counts too, stage or not, since it shares the
# mailbox. With neither, an entry already in the registry is a crash leftover:
# its stack is torn down and the key registered afresh. Without flock (macOS)
# only the label check remains, and two launches racing the same key in the
# same second can both pass it.
#
# stage_teardown runs from run.sh's EXIT trap, which bash also runs on HUP:
# the stack and its volumes go, and the registry entry with them.
#
# bash 3.2 compatible, like run.sh.

STAGE_KEY=
_stage_broker=
_stage_bus=

_stage_cli() {
  CLAUDE_DOCKER_BUS_DIR="$_stage_bus" python3 "$_stage_broker" "$@"
}

# stage_start BROKER BUS KEY PROJECT: register this box, or say why not and
# return 1. On success STAGE_KEY is set and stage_teardown has work to do.
stage_start() {
  local key=$3 project=$4 locks out rc
  _stage_broker=$1
  _stage_bus=$2
  if [ ! -f "$_stage_broker" ]; then
    echo "claude-docker: --stage: no broker at $_stage_broker" >&2
    return 1
  fi
  if command -v flock >/dev/null 2>&1; then
    locks="$HOME/.cache/claude-docker/locks"
    mkdir -p "$locks"
    exec 8>"$locks/stage-$key.lock"
    if ! flock -n 8; then
      echo "claude-docker: --stage: a live box already has the key $key" >&2
      return 1
    fi
  fi
  if [ -n "$(docker ps -q --filter "label=claude-docker.bus-key=$key" 2>/dev/null)" ]; then
    echo "claude-docker: --stage: a running container already has the key $key" >&2
    return 1
  fi
  rc=0
  out=$(_stage_cli register "$key" "$project" 2>&1) || rc=$?
  if [ "$rc" = 1 ]; then
    echo "claude-docker: --stage: clearing a stale stack for $key (crash leftover)" >&2
    _stage_cli teardown "$key" >/dev/null 2>&1 || true
    rc=0
    out=$(_stage_cli register "$key" "$project" 2>&1) || rc=$?
  fi
  if [ "$rc" != 0 ]; then
    echo "claude-docker: --stage $project: $out" >&2
    return 1
  fi
  STAGE_KEY=$key
}

# EXIT trap. Never fails. Quiet on success: after a HUP stderr is a dead
# terminal, and a failed write must not cost the teardown.
stage_teardown() {
  [ -n "$STAGE_KEY" ] || return 0
  _stage_cli teardown "$STAGE_KEY" >/dev/null 2>&1 \
    || echo "claude-docker: stage teardown failed; run: stage_broker.py teardown $STAGE_KEY" >&2 \
    || true
  STAGE_KEY=
}
