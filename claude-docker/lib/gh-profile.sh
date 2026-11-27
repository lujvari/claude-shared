# shellcheck shell=bash
# Named GitHub profiles, sourced by run.sh.
#
# --gh defaults to the owner's own token, and every source it has (the
# env-file op-ref, a GH_TOKEN/GITHUB_TOKEN in the shell or the env file, a gh
# login) leads back to it. A box for someone else's repos (cd-inat, on
# schubergphilis) takes none of them: its token comes only from its own
# op-ref, git offers it to github.com only, and anything missing aborts.
# Same shape as lib/ado-profile.sh.
#
# gh_profile_resolve reads WITH_GH, CLAUDE_DOCKER_GITHUB_PROFILE and the
# profile's op-ref, and always sets GH_PROFILE and GH_OP_REF_VAR (empty by
# default). For a profile it replaces the exported CLAUDE_DOCKER_GITHUB_OP_REF
# and CLAUDE_DOCKER_GITHUB_HOSTS, so run.sh's existing op preflight and read
# take the profile's ref and its gh CLI fallback stays off. On a bad profile
# it prints one error and returns 1. Every failure path returns explicitly:
# run.sh calls it as `gh_profile_resolve || exit 1`, which turns errexit off
# in here. bash 3.2 compatible, like run.sh.

gh_profile_resolve() {
  GH_PROFILE=""
  GH_OP_REF_VAR=""
  _gp_name=${CLAUDE_DOCKER_GITHUB_PROFILE:-}
  [ -n "$_gp_name" ] || return 0

  # Spelled-out class, not an a-z range: in some locales a bash 3.2 range
  # also matches upper case.
  _gp_lower=abcdefghijklmnopqrstuvwxyz
  case $_gp_name in
    *[!${_gp_lower}0123456789]*)
      echo "claude-docker: CLAUDE_DOCKER_GITHUB_PROFILE='$_gp_name' is not a profile name (lower-case letters and digits only)" >&2
      return 1 ;;
  esac
  [ "${WITH_GH:-0}" = "1" ] || return 0

  _gp_upper=$(printf '%s' "$_gp_name" | tr "$_gp_lower" ABCDEFGHIJKLMNOPQRSTUVWXYZ)
  GH_OP_REF_VAR="CLAUDE_DOCKER_GITHUB_${_gp_upper}_OP_REF"
  _gp_ref=${!GH_OP_REF_VAR:-}
  if [ -z "$_gp_ref" ]; then
    echo "claude-docker: GitHub profile '$_gp_name' needs $GH_OP_REF_VAR (op://vault/item/field); it never falls back to CLAUDE_DOCKER_GITHUB_OP_REF" >&2
    return 1
  fi

  GH_PROFILE=$_gp_name
  for _gp_var in GH_TOKEN GITHUB_TOKEN; do
    if [ -n "${!_gp_var:-}" ]; then
      echo "claude-docker: GitHub profile '$_gp_name': ignoring $_gp_var from the host; the profile's token comes from $GH_OP_REF_VAR" >&2
    fi
  done
  unset GH_TOKEN GITHUB_TOKEN
  export CLAUDE_DOCKER_GITHUB_OP_REF=$_gp_ref
  export CLAUDE_DOCKER_GITHUB_HOSTS=github.com
  return 0
}
