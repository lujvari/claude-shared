# shellcheck shell=bash
# Launch-time token probe, sourced by run.sh (openspec: add-token-probe).
#
# The fail-closed gate stops a launch whose credential flag injected nothing.
# It can't see a token that is present but dead, and three of the first ten
# box->host bus messages were exactly that: the box stalled at its first API
# call until someone rotated the token. So, once per credential flag on this
# launch, one cheap identity GET. A rejected token gets one warning line and
# the launch goes on; anything else (offline, timeout, 5xx, 403) is silent.
#
# Tokens never reach argv: each probe hands curl its url, header and user as a
# config on stdin (curl -K -), written with printf, which is a builtin. Output
# names the flag and the status code, nothing else.
#
# Claude Code repaints the terminal the moment the container starts, so the
# warning alone is gone before anyone reads it. The rejected flags are also
# left in TOKEN_PROBE_REJECTED (comma-separated, no dashes) for run.sh to hand
# to the in-container statusline.
#
# Reads the WITH_* flags and token variables run.sh has already resolved.
# bash 3.2 compatible, like run.sh.

# Escape a value for a double-quoted curl config string.
_tp_q() {
  _tp_s=${1//\\/\\\\}
  printf '%s' "${_tp_s//\"/\\\"}"
}

# _tp_get NAME KEY VALUE [KEY VALUE ...]: one GET in the background. The
# status lands in $_tp_dir/NAME.code ("000" when curl got no answer), the body
# in $_tp_dir/NAME.body.
_tp_get() {
  _tp_name=$1; shift
  {
    while [ "$#" -ge 2 ]; do
      printf '%s = "%s"\n' "$1" "$(_tp_q "$2")"
      shift 2
    done
  } | curl -K - -s -o "$_tp_dir/$_tp_name.body" -w '%{http_code}' \
      --connect-timeout 1 --max-time 2 >"$_tp_dir/$_tp_name.code" 2>/dev/null &
  _tp_pids="$_tp_pids $!"
}

_tp_code() { cat "$_tp_dir/$1.code" 2>/dev/null || true; }

_tp_warn() {
  TOKEN_PROBE_REJECTED="${TOKEN_PROBE_REJECTED:+$TOKEN_PROBE_REJECTED,}${1#--}"
  echo "claude-docker: $1 token rejected (HTTP $2) - rotate it on the host before relying on this box" >&2
}

# Warn for FLAG when probe NAME answered 401.
_tp_check401() {
  _tp_c=$(_tp_code "$2")
  [ "$_tp_c" = "401" ] && _tp_warn "$1" "$_tp_c"
  return 0
}

token_probe_all() {
  TOKEN_PROBE_REJECTED=""
  [ "${CLAUDE_DOCKER_NO_TOKEN_PROBE:-0}" = "1" ] && return 0
  command -v curl >/dev/null 2>&1 || return 0
  _tp_dir=$(mktemp -d "${TMPDIR:-/tmp}/claude-docker-probe.XXXXXX") || return 0
  _tp_pids=""

  _tp_gh="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if [ "${WITH_GH:-0}" = "1" ] && [ -n "$_tp_gh" ]; then
    _tp_get gh url "https://api.github.com/user" \
      header "Authorization: Bearer $_tp_gh"
  fi

  # GitLab: the token belongs to one of the enumerated hosts, so only a
  # rejection from every host means it is dead.
  _tp_glab_n=0
  if [ "${WITH_GLAB:-0}" = "1" ] && [ -n "${GITLAB_TOKEN:-}" ]; then
    for _tp_h in ${glab_hosts:-gitlab.com}; do
      _tp_glab_n=$((_tp_glab_n + 1))
      _tp_get "glab$_tp_glab_n" url "https://$_tp_h/api/v4/user" \
        header "PRIVATE-TOKEN: $GITLAB_TOKEN"
    done
  fi

  # ADO answers a bad credential with a 203 sign-in page unless told not to;
  # X-TFS-FedAuthRedirect: Suppress turns that into a 401.
  if [ -n "${CLAUDE_DOCKER_ADO_ORG:-}" ]; then
    _tp_ado_url="https://dev.azure.com/$CLAUDE_DOCKER_ADO_ORG/_apis/connectionData"
    if [ "${WITH_ADO:-0}" = "1" ] && [ -n "${AZURE_DEVOPS_EXT_PAT:-}" ]; then
      _tp_get ado url "$_tp_ado_url" user ":$AZURE_DEVOPS_EXT_PAT" \
        header "X-TFS-FedAuthRedirect: Suppress"
    fi
    if [ "${WITH_ADO_ADMIN:-0}" = "1" ] && [ -n "${AZURE_DEVOPS_ADMIN_PAT:-}" ]; then
      _tp_get ado_admin url "$_tp_ado_url" user ":$AZURE_DEVOPS_ADMIN_PAT" \
        header "X-TFS-FedAuthRedirect: Suppress"
    fi
  fi

  if [ "${WITH_JIRA:-0}" = "1" ] && [ -n "${JIRA_API_TOKEN:-}" ] \
     && [ -n "${JIRA_BASE_URL:-}" ] && [ -n "${JIRA_USER_EMAIL:-}" ]; then
    _tp_get jira url "${JIRA_BASE_URL%/}/rest/api/3/myself" \
      user "$JIRA_USER_EMAIL:$JIRA_API_TOKEN"
  fi

  if [ "${WITH_SUPABASE:-0}" = "1" ] && [ -n "${SUPABASE_ACCESS_TOKEN:-}" ]; then
    _tp_get supabase url "https://api.supabase.com/v1/projects" \
      header "Authorization: Bearer $SUPABASE_ACCESS_TOKEN"
  fi

  # Cloudflare: user tokens verify at /user, account-owned tokens only at
  # /accounts/<id>. Both are asked up front so the launch waits once.
  if [ "${WITH_CLOUDFLARE:-0}" = "1" ] && [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then
    _tp_get cf_user url "https://api.cloudflare.com/client/v4/user/tokens/verify" \
      header "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
    if [ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
      _tp_get cf_acct url "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/tokens/verify" \
        header "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
    fi
  fi

  if [ "${WITH_OPENROUTER:-0}" = "1" ] && [ -n "${OPENROUTER_API_KEY:-}" ]; then
    _tp_get openrouter url "https://openrouter.ai/api/v1/key" \
      header "Authorization: Bearer $OPENROUTER_API_KEY"
  fi

  if [ "${WITH_SONAR:-0}" = "1" ] && [ -n "${SONAR_TOKEN:-}" ]; then
    _tp_sonar="${SONAR_HOST_URL:-https://sonarcloud.io}"
    _tp_get sonar url "${_tp_sonar%/}/api/authentication/validate" \
      header "Authorization: Bearer $SONAR_TOKEN"
  fi

  if [ "${WITH_TFE:-0}" = "1" ] && [ -n "${TF_TOKEN_app_terraform_io:-}" ]; then
    _tp_get tfe url "https://app.terraform.io/api/v2/account/details" \
      header "Authorization: Bearer $TF_TOKEN_app_terraform_io"
  fi

  if [ "${WITH_HETZNER_INFRA:-0}" = "1" ] && [ -n "${HCLOUD_TOKEN:-}" ]; then
    _tp_get hetzner url "https://api.hetzner.cloud/v1/locations?per_page=1" \
      header "Authorization: Bearer $HCLOUD_TOKEN"
  fi

  for _tp_p in $_tp_pids; do wait "$_tp_p" 2>/dev/null || true; done

  _tp_check401 --gh gh

  if [ "$_tp_glab_n" -gt 0 ]; then
    _tp_all=1 _tp_i=1
    while [ "$_tp_i" -le "$_tp_glab_n" ]; do
      [ "$(_tp_code "glab$_tp_i")" = "401" ] || _tp_all=0
      _tp_i=$((_tp_i + 1))
    done
    [ "$_tp_all" = "1" ] && _tp_warn --glab 401
  fi

  _tp_check401 --ado ado
  _tp_check401 --ado-admin ado_admin
  _tp_check401 --jira jira
  _tp_check401 --supabase supabase

  # Cloudflare answers a bad token with 401 or 403 (code 1000, "Invalid API
  # Token"), and that is the only reason this endpoint refuses, so both count.
  _tp_c=$(_tp_code cf_user)
  case "$_tp_c" in
    401|403)
      if [ -f "$_tp_dir/cf_acct.code" ]; then
        case "$(_tp_code cf_acct)" in 401|403) _tp_warn --cloudflare "$_tp_c" ;; esac
      else
        _tp_warn --cloudflare "$_tp_c"
      fi ;;
  esac

  _tp_check401 --openrouter openrouter

  # SonarCloud answers 200 {"valid":false} for a bad token, not 401.
  _tp_c=$(_tp_code sonar)
  if [ "$_tp_c" = "401" ]; then
    _tp_warn --sonar 401
  elif [ "$_tp_c" = "200" ] && grep -Eq '"valid"[[:space:]]*:[[:space:]]*false' "$_tp_dir/sonar.body" 2>/dev/null; then
    _tp_warn --sonar '200, valid:false'
  fi

  _tp_check401 --tfe tfe
  _tp_check401 --hetzner-infra hetzner

  rm -rf "$_tp_dir"
  return 0
}
