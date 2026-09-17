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
#
# "$@" MUST stay last. Everything after `--` is forwarded verbatim to claude,
# so a workspace path sitting after "$@" gets swallowed as a claude argument
# and the mount silently falls back to $PWD.
