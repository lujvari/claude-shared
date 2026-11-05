# Shared helpers for the claude-docker launchers in this directory.
#
# Sourced, never symlinked onto PATH — hence the leading underscore and the
# .sh suffix its siblings deliberately lack: those are the command names
# themselves (cd-ct, not cd-ct.sh), symlinked into ~/bin, which stock
# ~/.profile puts on PATH. Nothing here touches a shell rc — no functions
# defined in the caller's shell, no DEV to export, nothing to re-source.

# Dev root, derived from this file's own resolved location. Layout is
#   $DEV/tools/claude-shared/claude-docker/launchers/_lib.sh
# so the root sits four directories above this one. Derived rather than
# configured: relocating the clone needs no edit here or in any launcher.
_cd_lib_dir=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)
CD_RUN="$_cd_lib_dir/../run.sh"
DEV=$(cd "$_cd_lib_dir/../../../.." && pwd)
# Exported for run.sh, which resolves +PATH workspaces against it.
export CLAUDE_DOCKER_DEV_ROOT="$DEV"

# Every launched box gets its own agent-bus mailbox under the dev root (see
# --no-bus in run.sh). Exported, not passed as a flag, so run.sh stays usable
# without it; an explicit CLAUDE_DOCKER_BUS_DIR still wins.
export CLAUDE_DOCKER_BUS_DIR="${CLAUDE_DOCKER_BUS_DIR:-$DEV/.agent-bus}"

# Every launched box gets the remote Brain MCP (--brain in run.sh). The same
# exported-not-flagged split as the bus. It fails closed, so a launcher whose
# Brain refs don't resolve is blocked. Export CLAUDE_DOCKER_BRAIN=0 to opt out.
export CLAUDE_DOCKER_BRAIN="${CLAUDE_DOCKER_BRAIN:-1}"

# cd_workspace <path-relative-to-dev-root>
#
# Sets $ws to the absolute workspace path, failing loudly when it is missing.
# Worth checking: run.sh defaults an absent workspace to $PWD, so a typo or a
# moved checkout would otherwise mount the wrong tree without complaint.
cd_workspace() {
  ws="$DEV/$1"
  [ -d "$ws" ] && return 0
  local me
  me=$(basename "$0")
  echo "$me: workspace not found: $ws" >&2
  echo "$me: dev root derived as '$DEV' from '$_cd_lib_dir'." >&2
  echo "$me: if the checkout moved, fix the derivation in _lib.sh." >&2
  exit 1
}

# Every launcher ends with:  exec "$CD_RUN" <wrapper-flags> "$ws" "$@"
# (or cd_test_db_run in place of exec "$CD_RUN"; see below).
#
# "$@" MUST stay last. Everything after `--` is forwarded verbatim to claude,
# so a workspace path sitting after "$@" gets swallowed as a claude argument
# and the mount silently falls back to $PWD.

# Test-database lifecycle, for launchers that bring up a project's disposable
# test Postgres (cd-brain, cd-mep). Such a launcher calls
#   cd_test_db_hold <container>      before its `up`
#   cd_test_db_run  <container> <run.sh args...> "$@"   instead of `exec`
# and the last box of that project to exit stops the database: `docker stop`
# on every container of its compose project, never `down`, so containers and
# volumes survive and the next launch's `up --wait` restarts them.
#
# "Last box" is a lock, not a count of running containers. Each launcher holds
# a shared flock on ~/.cache/claude-docker/locks/<container>.lock from before
# its `up` until its box exits, so a box still between `up` and `docker run`
# (op reads, token probe — seconds) counts as running and the database isn't
# stopped under it. On exit the launcher converts its lock to exclusive without
# waiting; only the last holder gets it. A launch that starts during a stop
# waits for it in cd_test_db_hold, then brings the database back up. The lock
# fd is inherited by run.sh and the docker CLI, so a launcher killed outright
# leaves the lock held for as long as its session still runs.
#
# cd_test_db_run never returns, it exits with the box's status: once a launcher
# outlives its first read, editing it mid-session (a git pull) would make bash
# resume at a stale byte offset on exit — the hazard described at the top of
# run.sh. Nothing in the launcher after this call is ever read.
_cd_test_db=
_cd_test_db_owned=0

cd_test_db_hold() {
  local locks="$HOME/.cache/claude-docker/locks"
  _cd_test_db=$1
  if ! command -v flock >/dev/null 2>&1; then
    printf '%s: no flock; %s stays up after this box\n' "$(basename "$0")" "$1" >&2
    return 0
  fi
  mkdir -p "$locks"
  exec 9>"$locks/$1.lock"
  if flock -s -w 60 9; then
    _cd_test_db_owned=1
  else
    printf '%s: lock wait timed out; %s stays up after this box\n' "$(basename "$0")" "$1" >&2
  fi
}

cd_test_db_run() {
  local rc=0
  _cd_test_db=$1
  shift
  trap _cd_test_db_release EXIT
  # Mapped to exits so the EXIT trap runs on them too. A closed terminal is
  # HUP. Under -it, Ctrl-C reaches claude inside the box, not this shell.
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  "$CD_RUN" "$@" || rc=$?
  exit "$rc"
}

# EXIT trap. Never fails and never calls exit, so the launcher keeps the box's
# status. Reports after acting: after a HUP stderr is a dead terminal, and a
# failed write must not cost the stop.
_cd_test_db_release() {
  local c=$_cd_test_db p msg ids=()
  set +e
  [ "$_cd_test_db_owned" = 1 ] || return 0
  if ! flock -xn 9; then
    msg="$c left running: another box holds it"
  else
    p=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$c" 2>/dev/null)
    # shellcheck disable=SC2207 # container ids: no spaces, no globs
    [ -n "$p" ] && ids=($(docker ps -q --filter "label=com.docker.compose.project=$p" 2>/dev/null))
    if [ -z "$p" ]; then
      msg="$c not stopped: no such container, or no compose project label"
    elif [ "${#ids[@]}" = 0 ]; then
      msg="$c already stopped"
    elif docker stop "${ids[@]}" >/dev/null 2>&1; then
      msg="$c stopped (last box out)"
    else
      msg="$c: docker stop failed; still running"
    fi
  fi
  # Unlocks the open file description itself, so a launch waiting in
  # cd_test_db_hold proceeds even if some stray child still holds fd 9.
  flock -u 9
  printf '%s\n' "$msg" >&2 2>/dev/null
  return 0
}
