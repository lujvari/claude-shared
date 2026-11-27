# shellcheck shell=bash
# Named Azure DevOps profiles, sourced by run.sh.
#
# --ado was built for one org. A second one (a customer org next to the SBP
# one) needs its own PAT, and an SBP PAT must never reach that box. Every
# default --ado has (the env-file op-ref, a host AZURE_DEVOPS_EXT_PAT, a
# helper for all of dev.azure.com) leads back to SBP, so a named profile
# takes nothing from them: its PAT comes only from its own op-ref, its git
# helper answers only for its own orgs, and anything missing aborts.
#
# ado_profile_resolve reads WITH_ADO, WITH_ADO_ADMIN, CLAUDE_DOCKER_ADO_PROFILE
# and the profile's own variables, and always sets ADO_PROFILE, ADO_OP_REF_VAR
# and ADO_OP_REF (empty by default); a profile's orgs go out through the
# exported CLAUDE_DOCKER_ADO_ORG and CLAUDE_DOCKER_ADO_HOSTS. On a bad profile it prints one
# error and returns 1. Every failure path returns explicitly: run.sh calls it
# as `ado_profile_resolve || exit 1`, which turns errexit off in here.
# bash 3.2 compatible, like run.sh.

ado_profile_resolve() {
  ADO_PROFILE=""
  ADO_OP_REF_VAR=""
  ADO_OP_REF=""
  _ap_name=${CLAUDE_DOCKER_ADO_PROFILE:-}

  if [ -z "$_ap_name" ]; then
    ADO_OP_REF=${CLAUDE_DOCKER_ADO_OP_REF:-}
    return 0
  fi

  # Spelled-out classes, not a-z ranges: in some locales a bash 3.2 range
  # also matches upper case.
  _ap_lower=abcdefghijklmnopqrstuvwxyz
  _ap_alnum=${_ap_lower}ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
  case $_ap_name in
    *[!${_ap_lower}0123456789]*)
      echo "claude-docker: CLAUDE_DOCKER_ADO_PROFILE='$_ap_name' is not a profile name (lower-case letters and digits only)" >&2
      return 1 ;;
  esac
  # The admin PAT is SBP's; a profile has no admin variant.
  if [ "${WITH_ADO_ADMIN:-0}" = "1" ]; then
    echo "claude-docker: --ado-admin can't be used with ADO profile '$_ap_name' (CLAUDE_DOCKER_ADO_PROFILE)" >&2
    return 1
  fi
  [ "${WITH_ADO:-0}" = "1" ] || return 0

  _ap_upper=$(printf '%s' "$_ap_name" | tr "$_ap_lower" ABCDEFGHIJKLMNOPQRSTUVWXYZ)
  ADO_OP_REF_VAR="CLAUDE_DOCKER_ADO_${_ap_upper}_OP_REF"
  _ap_orgs_var="CLAUDE_DOCKER_ADO_${_ap_upper}_ORGS"
  ADO_OP_REF=${!ADO_OP_REF_VAR:-}
  _ap_orgs=${!_ap_orgs_var:-}

  if [ -z "$ADO_OP_REF" ]; then
    echo "claude-docker: ADO profile '$_ap_name' needs $ADO_OP_REF_VAR (op://vault/item/field); it never falls back to CLAUDE_DOCKER_ADO_OP_REF" >&2
    return 1
  fi
  # Orgs go into git config keys and URLs: letters, digits and hyphens only,
  # no empty items. Kept as spelled, since git matches the path case-sensitively.
  case ",$_ap_orgs," in
    ,,|*,,*|*[!${_ap_alnum},-]*)
      echo "claude-docker: ADO profile '$_ap_name' needs $_ap_orgs_var as a comma list of org names (got '$_ap_orgs')" >&2
      return 1 ;;
  esac

  ADO_PROFILE=$_ap_name
  if [ -n "${AZURE_DEVOPS_EXT_PAT:-}" ]; then
    echo "claude-docker: ADO profile '$_ap_name': ignoring AZURE_DEVOPS_EXT_PAT from the host; the profile's PAT comes from $ADO_OP_REF_VAR" >&2
  fi
  unset AZURE_DEVOPS_EXT_PAT
  # The probe reads the org list from CLAUDE_DOCKER_ADO_ORG. The entrypoint's
  # credential helper is keyed on credential.https://<host>, which matches a
  # path too, so dev.azure.com/<org> scopes the PAT to its orgs with no
  # entrypoint change.
  export CLAUDE_DOCKER_ADO_ORG=$_ap_orgs
  CLAUDE_DOCKER_ADO_HOSTS="dev.azure.com/${_ap_orgs//,/,dev.azure.com/}"
  export CLAUDE_DOCKER_ADO_HOSTS
  return 0
}
