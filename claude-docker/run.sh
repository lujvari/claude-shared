#!/usr/bin/env bash
set -euo pipefail

# Real on-disk directory of this launcher, resolved through any symlinks (the
# ~/bin/claude-docker launcher is typically a symlink into the repo). Used both
# to locate wrapper-shipped assets (e.g. hooks/) that get mounted into every
# container regardless of the user's host ~/.claude config, AND to protect the
# launcher's own directory when a broad workspace mount sweeps it in (see the
# read-only overlay in the workspace loop below). Resolving the symlink is
# load-bearing: a plain `dirname "${BASH_SOURCE[0]}"` yields the symlink's own
# dir (e.g. ~/bin), so the wrapper-asset lookups below would silently find
# nothing and the container would fall back to the host's ~/.claude hooks.
self_src="${BASH_SOURCE[0]}"
while [ -h "$self_src" ]; do
  self_ldir=$(cd -P "$(dirname "$self_src")" && pwd)
  self_link=$(readlink "$self_src")
  case "$self_link" in /*) self_src="$self_link" ;; *) self_src="$self_ldir/$self_link" ;; esac
done
SELF_DIR=$(cd -P "$(dirname "$self_src")" && pwd)

# Override via CLAUDE_DOCKER_IMAGE so child images (FROM claude-code:local) can
# reuse this wrapper's full feature set — credential opt-ins, statusline tag,
# git-identity forwarding, host-config bind-mounts — without forking it.
IMAGE="${CLAUDE_DOCKER_IMAGE:-claude-code:local}"

# Keep this in sync with the flag-parsing case statement below — adding or
# removing a wrapper flag means updating both the case branch and this heredoc
# in the same diff.
print_help() {
  cat <<'EOF'
Usage: claude-docker [OPTIONS] [WORKSPACE...] [-- CLAUDE_FLAGS...]

Hardened Docker wrapper for Claude Code. Wrapper flags and workspace paths
are parsed before `--`; anything after `--` is forwarded verbatim to the
`claude` binary inside the container.

Workspaces:
  WORKSPACE...        One or more host directories to mount at
                      /workspaces/<basename>. Defaults to $PWD when omitted.
                      First workspace becomes the container's working dir;
                      every additional workspace is passed to claude as
                      --add-dir so the agent can read/write across all of them.

Wrapper flags:
  -h, --help          Print this help and exit 0 without starting Docker.
  --yolo              Pass --dangerously-skip-permissions to claude.
  --ephemeral         Skip the claude-code-root/claude-code-home named
                      volumes. No OAuth token, gh login, shell history, or
                      session history persists across runs.
  --ro                Mount every workspace read-only (review / audit mode).
  --tools             Mount this launcher's OWN directory read-WRITE. By
                      default, if a broad workspace mount sweeps the launcher
                      dir in (e.g. mounting all of C:\dev pulls it in under
                      tools/), that one directory is overlaid read-only so a
                      --yolo container can't rewrite the host launcher or its
                      shipped hooks and have the host run them on the next
                      start. Only the launcher dir is pinned — the rest of the
                      workspace, including everything else under tools/, stays
                      writable. Pass --tools only when you need to edit the
                      launcher itself from inside the container.
  --aws               Opt in to AWS: mount ~/.aws/config + ~/.aws/sso (:ro)
                      and forward AWS_PROFILE / AWS_REGION /
                      AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
                      AWS_SESSION_TOKEN when set. 1Password fallback
                      via CLAUDE_DOCKER_AWS_OP_REF (`op read` on host)
                      resolves fields access_key_id, secret_access_key,
                      and optionally session_token / region.
  --gh                Opt in to GitHub: forward GH_TOKEN / GITHUB_TOKEN and
                      unmask in-container gh login state.
  --glab              Opt in to GitLab: mount glab-cli config (:ro) and
                      forward GITLAB_TOKEN; unmask in-container glab login.
  --tfe               Opt in to Terraform Cloud (app.terraform.io): mount
                      ~/.terraform.d/credentials.tfrc.json (:ro) when
                      present and forward TF_TOKEN_app_terraform_io;
                      unmask in-container `terraform login` state.
  --tofu              Opt in to OpenTofu against app.terraform.io: mount
                      ~/.tofurc (:ro) when present, mount the shared
                      ~/.terraform.d/credentials.tfrc.json (:ro), and
                      forward TF_TOKEN_app_terraform_io; unmask
                      in-container `tofu login` state.
  --ado               Opt in to Azure DevOps: forward AZURE_DEVOPS_EXT_PAT
                      and inject a system-level git insteadOf rewrite for
                      dev.azure.com so in-container `git clone` against
                      private Azure Repos works without prompting.
  --jira              Opt in to Atlassian Jira (Cloud): forward
                      JIRA_USER_EMAIL / JIRA_BASE_URL / JIRA_API_TOKEN so
                      in-container scripts can hit the Jira REST API
                      (Basic auth = email:api-token). 1Password fallback
                      via CLAUDE_DOCKER_JIRA_OP_REF (`op read` on host).
  --claude-auth       Share the HOST Claude login with the container:
                      bind-mount <config-dir>/.credentials.json (read-write)
                      over /root/.claude/.credentials.json so host and
                      container use one OAuth token and refreshes propagate
                      both ways. Ends the periodic in-container 401 / "run
                      /login" that happens when a host re-login rotates the
                      account token. Security: a --yolo container can then
                      read/write your real Claude credential — a prompt-
                      injected workspace file could exfiltrate it. Off by
                      default. Env: CLAUDE_DOCKER_CONFIG_DIR sets the source.
  --iterm             Wrap claude in tmux -CC (iTerm2 control mode → native
                      panes). Equivalent to CLAUDE_DOCKER_TMUX=cc.
  --tmux              Wrap claude in plain tmux (works in any terminal).
                      Equivalent to CLAUDE_DOCKER_TMUX=1.
  --claude-dir=PATH   Use PATH as the host Claude config dir instead of
                      ~/.claude. Affects agents, commands, skills, CLAUDE.md,
                      and statusline. Env: CLAUDE_DOCKER_CONFIG_DIR.

Separator:
  --                  Ends wrapper-flag parsing. Everything after is passed
                      to `claude`, e.g. `claude-docker ~/repo -- --resume`.

Environment:
  CLAUDE_DOCKER_TMUX       1  → plain tmux wrapper (same as --tmux).
                           cc → tmux -CC iTerm2 control mode (same as
                           --iterm).
  CLAUDE_DOCKER_IMAGE      Override the image tag (default: claude-code:local).
                           Used by child images that extend this one and want to
                           reuse this wrapper.
  CLAUDE_DOCKER_CONFIG_DIR Override the host Claude config dir (same as
                           --claude-dir=PATH).

Credentials are off by default; combine opt-ins as needed:
  claude-docker --aws --gh ~/repo

Git identity (user.name, user.email) is forwarded automatically from the
host's global git config as GIT_AUTHOR_* / GIT_COMMITTER_* env vars so
in-container `git commit` works without a `-c user.email=...` override.
Not gated: identity is already public on every commit you've ever made.
Signing, credential helpers, and hooks are NOT forwarded.

If <config-dir>/settings.docker.json exists it is mounted read-only as a
seed and copied onto a writable settings.json on every container start, so
in-session writes like /effort work and reset to the seed next start; the
regular settings.json is never forwarded automatically.
EOF
}

# Wrapper flags and workspace paths before `--`; verbatim claude flags after.
# See `print_help` above or `claude-docker --help` for the flag list.
WORKSPACES=()
CLAUDE_FLAGS=()
EPHEMERAL=0
RO_WORKSPACES=0
WITH_TOOLS_RW=0
WITH_AWS=0
WITH_GH=0
WITH_GLAB=0
WITH_TFE=0
WITH_TOFU=0
WITH_ADO=0
WITH_JIRA=0
WITH_CLAUDE_AUTH=0
CLAUDE_CONFIG_DIR="${CLAUDE_DOCKER_CONFIG_DIR:-$HOME/.claude}"
saw_sep=0
for arg in "$@"; do
  if [ "$arg" = "--" ]; then saw_sep=1; continue; fi
  if [ "$saw_sep" = "1" ]; then
    CLAUDE_FLAGS+=("$arg"); continue
  fi
  case "$arg" in
    -h|--help)      print_help; exit 0 ;;
    --yolo)         CLAUDE_FLAGS+=("--dangerously-skip-permissions") ;;
    --ephemeral)    EPHEMERAL=1 ;;
    --ro)           RO_WORKSPACES=1 ;;
    --tools)        WITH_TOOLS_RW=1 ;;
    --aws)          WITH_AWS=1 ;;
    --gh)           WITH_GH=1 ;;
    --glab)         WITH_GLAB=1 ;;
    --tfe)          WITH_TFE=1 ;;
    --tofu)         WITH_TOFU=1 ;;
    --ado)          WITH_ADO=1 ;;
    --jira)         WITH_JIRA=1 ;;
    --claude-auth)  WITH_CLAUDE_AUTH=1 ;;
    --iterm)        CLAUDE_DOCKER_TMUX=cc ;;
    --tmux)         CLAUDE_DOCKER_TMUX=1 ;;
    --claude-dir=*) CLAUDE_CONFIG_DIR="${arg#--claude-dir=}" ;;
    -*)             echo "claude-docker: unknown flag '$arg' (use -- to pass flags to claude)" >&2; exit 1 ;;
    *)              WORKSPACES+=("$arg") ;;
  esac
done
[ "${#WORKSPACES[@]}" -eq 0 ] && WORKSPACES=("$PWD")
# Expand a leading ~/ in CLAUDE_CONFIG_DIR — needed when set via env var, where
# the shell does not perform tilde expansion. Pattern is "~/" not "~" so a
# user-tilde form like "~alice/path" is not silently misresolved as "$HOME/alice/path".
# shellcheck disable=SC2088  # literal "~/" is the intended case pattern, not a tilde-expansion target
case "$CLAUDE_CONFIG_DIR" in "~/"*) CLAUDE_CONFIG_DIR="$HOME/${CLAUDE_CONFIG_DIR#\~/}" ;; esac

MOUNT_ARGS=()
ENV_ARGS=(-e TERM)
CONTAINER_PATHS=()

ws_suffix=""
[ "$RO_WORKSPACES" = "1" ] && ws_suffix=":ro"

# Parallel arrays (not associative) so macOS system bash 3.2 works.
# Counter-based iteration avoids ${!arr[@]} which trips set -u on empty arrays.
SEEN_NAMES=()
SEEN_PATHS=()
for ws in "${WORKSPACES[@]}"; do
  abs=$(cd "$ws" && pwd)
  name=$(basename "$abs")
  case "$name" in
    *[!A-Za-z0-9._-]*|"")
      echo "claude-docker: workspace basename '$name' contains characters that break 'docker -v' parsing; allowed: [A-Za-z0-9._-]" >&2
      exit 1 ;;
  esac
  n=${#SEEN_NAMES[@]}
  i=0
  while [ "$i" -lt "$n" ]; do
    if [ "${SEEN_NAMES[$i]}" = "$name" ]; then
      echo "claude-docker: workspace basename collision — '$abs' and '${SEEN_PATHS[$i]}' both map to /workspaces/$name" >&2
      exit 1
    fi
    i=$((i + 1))
  done
  SEEN_NAMES+=("$name")
  SEEN_PATHS+=("$abs")
  MOUNT_ARGS+=("-v" "$abs:/workspaces/$name$ws_suffix")
  # Safeguard: if this launcher's own directory got swept into a broad
  # workspace mount (e.g. mounting all of C:\dev pulls it in under tools/),
  # overlay just that one directory read-only. An in-container (root, --yolo)
  # process could otherwise rewrite the host launcher or its shipped hooks/ and
  # have the host execute them on the next start (container -> host
  # persistence). Only the launcher dir is pinned — the rest of the workspace,
  # including everything else under tools/, stays writable. Docker resolves the
  # nested bind mount by path depth, so the :ro child wins over the rw parent;
  # the kernel enforces it (root + DAC_OVERRIDE/FOWNER can't write through ro).
  # The "$abs"/* pattern matches only when SELF_DIR is strictly below the
  # workspace, so mounting the launcher dir itself stays fully writable.
  # --tools opts back into rw; --ro already makes the whole parent read-only.
  if [ "$RO_WORKSPACES" != "1" ] && [ "$WITH_TOOLS_RW" != "1" ]; then
    case "$SELF_DIR" in
      "$abs"/*)
        sub="${SELF_DIR#"$abs"}"
        MOUNT_ARGS+=("-v" "$SELF_DIR:/workspaces/$name$sub:ro") ;;
    esac
  fi
  CONTAINER_PATHS+=("/workspaces/$name")
done
CWD="${CONTAINER_PATHS[0]}"

# File-based host creds. gh uses macOS Keychain → log in inside the container once; persists via claude-code-root.
# glab on macOS lives under ~/Library/Application Support/glab-cli (not XDG); fall back to ~/.config/glab-cli on Linux.
if [ "$WITH_GLAB" = "1" ]; then
  glab_src=""
  if [ -d "$HOME/Library/Application Support/glab-cli" ]; then
    glab_src="$HOME/Library/Application Support/glab-cli"
  elif [ -d "$HOME/.config/glab-cli" ]; then
    glab_src="$HOME/.config/glab-cli"
  fi
  [ -n "$glab_src" ] && MOUNT_ARGS+=("-v" "$glab_src:/root/.config/glab-cli:ro")
fi

# Scoped AWS mount: only non-secret config + short-lived SSO bearer cache.
# Excludes ~/.aws/credentials (long-lived access keys) and ~/.aws/cli/cache
# (cached assume-role STS). Env-var flow (AWS_ACCESS_KEY_ID/...) still forwards
# below for users who flatten creds with `aws configure export-credentials`,
# and CLAUDE_DOCKER_AWS_OP_REF resolves access keys from 1Password as a
# host-less fallback — see the --aws OP fallback block further down.
if [ "$WITH_AWS" = "1" ]; then
  [ -f "$HOME/.aws/config" ] && MOUNT_ARGS+=("-v" "$HOME/.aws/config:/root/.aws/config:ro")
  [ -d "$HOME/.aws/sso" ]    && MOUNT_ARGS+=("-v" "$HOME/.aws/sso:/root/.aws/sso:ro")
fi

# Terraform Cloud credentials file written by `terraform login` (and `tofu
# login` — OpenTofu reuses the same path for back-compat). Standard location
# on every platform is ~/.terraform.d/credentials.tfrc.json. Only
# app.terraform.io is in scope here; the file format supports other hosts
# but mounting them is intentional and out of scope. Gated on either --tfe
# or --tofu; combined `--tfe --tofu` produces a duplicate `-v src:dst:ro`
# which docker handles idempotently.
if [ "$WITH_TFE" = "1" ] || [ "$WITH_TOFU" = "1" ]; then
  [ -f "$HOME/.terraform.d/credentials.tfrc.json" ] \
    && MOUNT_ARGS+=("-v" "$HOME/.terraform.d/credentials.tfrc.json:/root/.terraform.d/credentials.tfrc.json:ro")
fi

# OpenTofu CLI config file. Distinct from ~/.terraformrc — holds tofu-specific
# blocks (provider mirrors, plugin cache, dev_overrides). Not credentials, so
# no tmpfs leak guard is applied for /root/.tofurc when --tofu is unset;
# residual config from a prior --tofu session via claude-code-root is
# documented in the threat model.
if [ "$WITH_TOFU" = "1" ]; then
  [ -f "$HOME/.tofurc" ] && MOUNT_ARGS+=("-v" "$HOME/.tofurc:/root/.tofurc:ro")
fi

ENV_VARS=()
[ "$WITH_GH" = "1" ]   && ENV_VARS+=(GH_TOKEN GITHUB_TOKEN)
[ "$WITH_GLAB" = "1" ] && ENV_VARS+=(GITLAB_TOKEN)
[ "$WITH_AWS" = "1" ]  && ENV_VARS+=(AWS_PROFILE AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN)
if [ "$WITH_TFE" = "1" ] || [ "$WITH_TOFU" = "1" ]; then
  ENV_VARS+=(TF_TOKEN_app_terraform_io)
fi
[ "$WITH_ADO" = "1" ] && ENV_VARS+=(AZURE_DEVOPS_EXT_PAT)
# JIRA_USER_EMAIL + JIRA_BASE_URL are non-secret (email + site URL); only
# JIRA_API_TOKEN is a secret. All three are forwarded as a unit because
# the in-container Jira REST scripts need all three to function (Basic
# auth pairs the email with the token; the URL routes the request).
[ "$WITH_JIRA" = "1" ] && ENV_VARS+=(JIRA_USER_EMAIL JIRA_BASE_URL JIRA_API_TOKEN)
# Guarded: bash 3.2 under `set -u` errors on empty-array expansion.
if [ "${#ENV_VARS[@]}" -gt 0 ]; then
  for v in "${ENV_VARS[@]}"; do
    [ -n "${!v:-}" ] && ENV_ARGS+=("-e" "$v")
  done
fi
# Enumerate authenticated hosts from gh/glab config files so the container
# entrypoint can apply `git config --system url.<host>.insteadOf` for each.
# Parsing is best-effort: on missing/unreadable/unparseable config, output
# is empty and the entrypoint falls back to the canonical public host. The
# config dirs may also be unreadable from inside the container (uid 0 + no
# CAP_DAC_OVERRIDE vs uid 1000 mode 0700 dirs), which is why we parse on
# the host where the user owns the files.
#
# gh: ~/.config/gh/hosts.yml — hostnames are top-level keys. Require at
# least one dot in the key (every real GH host has one) so a future
# unrelated top-level key doesn't get treated as a host.
_extract_gh_hosts() {
  local cfg="$HOME/.config/gh/hosts.yml"
  [ -r "$cfg" ] || return 0
  awk '/^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z0-9-]+:[[:space:]]*$/ { sub(":[[:space:]]*$", ""); print }' "$cfg" \
    | paste -sd, -
}
# glab: ~/.config/glab-cli/config.yml — hosts are nested under a `hosts:`
# key. glab 1.97+ uses 4-space indent (1.92 used 2-space). Per-host
# config keys live one level deeper (subfolder:, proxy:, api_protocol:
# etc.) and also end with a colon. Match any indent depth and require a
# dot in the key name to disambiguate from those config keys (none of
# which contain dots).
_extract_glab_hosts() {
  local cfg="$HOME/.config/glab-cli/config.yml"
  [ -r "$cfg" ] || return 0
  awk '
    /^hosts:[[:space:]]*$/ { in_hosts=1; next }
    in_hosts && /^[^[:space:]]/ { in_hosts=0 }
    in_hosts && /^[[:space:]]+[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z0-9-]+:[[:space:]]*$/ {
      sub("^[[:space:]]+", ""); sub(":[[:space:]]*$", ""); print
    }
  ' "$cfg" | paste -sd, -
}

# Compute host lists once per flag — reused for both the token fallback
# below and CLAUDE_DOCKER_*_HOSTS forwarding to the entrypoint. Honor a
# pre-set CLAUDE_DOCKER_*_HOSTS env var as an explicit override / escape
# hatch when config parsing doesn't fit the user's setup.
gh_hosts=""
glab_hosts=""
if [ "$WITH_GH" = "1" ]; then
  gh_hosts="${CLAUDE_DOCKER_GITHUB_HOSTS:-$(_extract_gh_hosts || true)}"
fi
if [ "$WITH_GLAB" = "1" ]; then
  glab_hosts="${CLAUDE_DOCKER_GITLAB_HOSTS:-$(_extract_glab_hosts || true)}"
fi

# --gh fallback: if neither GH_TOKEN nor GITHUB_TOKEN was forwarded, walk
# enumerated GitHub hosts (or default github.com) and call
# `gh auth token --hostname <host>` until one returns a token. Users
# authenticated only against a GH Enterprise host (not github.com) would
# otherwise get an empty token from plain `gh auth token` (which defaults
# to github.com) and silently lose the auto-injection. Silent on failure
# (gh absent or not logged into any enumerated host).
if [ "$WITH_GH" = "1" ] && [ -z "${GH_TOKEN:-}" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
  if command -v gh >/dev/null 2>&1; then
    candidates="${gh_hosts:-github.com}"
    old_ifs=$IFS; IFS=','
    for host in $candidates; do
      [ -n "$host" ] || continue
      gh_token=$(gh auth token --hostname "$host" 2>/dev/null || true)
      if [ -n "$gh_token" ]; then
        GH_TOKEN="$gh_token"
        export GH_TOKEN
        ENV_ARGS+=("-e" "GH_TOKEN")
        break
      fi
    done
    IFS=$old_ifs
  fi
fi

# --glab fallback: parse the glab config file directly to extract the
# token for each enumerated host (or default gitlab.com when enumeration
# is empty). We deliberately do NOT call `glab auth token` here because
# that subcommand isn't present across glab releases (1.97 doesn't have
# it; the documented method is `glab auth status --show-token` whose
# output is human-formatted). The on-disk YAML config has a stable
# schema across versions and is owned by the invoking user (uid 1000),
# so it's the most reliable source.
if [ "$WITH_GLAB" = "1" ] && [ -z "${GITLAB_TOKEN:-}" ]; then
  cfg="$HOME/.config/glab-cli/config.yml"
  if [ -r "$cfg" ]; then
    candidates="${glab_hosts:-gitlab.com}"
    old_ifs=$IFS; IFS=','
    for host in $candidates; do
      [ -n "$host" ] || continue
      glab_token=$(awk -v target="$host" '
        function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
        BEGIN { in_host = 0 }
        {
          t = trim($0)
          if (t == target ":") { in_host = 1; next }
          if (in_host && t ~ /^[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z0-9-]+:$/) in_host = 0
          if (in_host && t ~ /^token:[[:space:]]+/) {
            sub(/^token:[[:space:]]+/, "", t); sub(/[[:space:]]+$/, "", t)
            gsub(/^"|"$/, "", t)
            print t; exit
          }
        }
      ' "$cfg" 2>/dev/null)
      if [ -n "$glab_token" ]; then
        GITLAB_TOKEN="$glab_token"
        export GITLAB_TOKEN
        ENV_ARGS+=("-e" "GITLAB_TOKEN")
        break
      fi
    done
    IFS=$old_ifs
  fi
fi

# Hard-timeout wrapper around `op read`. Without it, a 1Password/network
# outage makes each read hang until the TCP connect times out; across the
# up-to-6 sequential reads below (4 for --aws, 1 each for --ado/--jira) that
# silently added minutes to startup and dropped the creds with no message
# (the old `2>/dev/null || true` swallowed the failure). Now each read is
# capped at CLAUDE_DOCKER_OP_TIMEOUT seconds (default 5) and a warning naming
# the ref is emitted on each timeout. Returns empty + non-zero so callers' existing
# non-empty checks no-op the fallback exactly as before. `timeout` is
# coreutils (gtimeout on macOS via brew); when neither is present we fall back
# to a plain read so behaviour is unchanged on hosts without it.
OP_READ_TIMEOUT="${CLAUDE_DOCKER_OP_TIMEOUT:-5}"
if command -v timeout >/dev/null 2>&1; then OP_TIMEOUT_BIN=timeout
elif command -v gtimeout >/dev/null 2>&1; then OP_TIMEOUT_BIN=gtimeout
else OP_TIMEOUT_BIN=""; fi
op_read() {
  op_out=""; op_rc=0
  if [ -n "$OP_TIMEOUT_BIN" ]; then
    op_out=$("$OP_TIMEOUT_BIN" "$OP_READ_TIMEOUT" op read "$1" 2>/dev/null); op_rc=$?
  else
    op_out=$(op read "$1" 2>/dev/null); op_rc=$?
  fi
  # 124 = timeout tripped. Each call site runs op_read in a $(...) subshell,
  # so a shared "warn once" flag wouldn't survive back to the parent — warn
  # per timed-out read instead, naming the ref so the line stays useful. The
  # ref is an op:// path, not the secret, so it's safe to print.
  if [ "$op_rc" -eq 124 ]; then
    echo "claude-docker: 'op read $1' timed out after ${OP_READ_TIMEOUT}s — 1Password unreachable (check VPN / WSL2 egress); skipping this credential." >&2
    return 1
  fi
  printf '%s' "$op_out"
  return "$op_rc"
}

# --aws fallback: when AWS_ACCESS_KEY_ID isn't pre-set on the host AND no
# host-side AWS state will produce env-var creds (no `aws sso login` cache
# active, no `aws configure export-credentials` exported), read static
# access keys from 1Password via `op read "$CLAUDE_DOCKER_AWS_OP_REF/<field>"`.
# CLAUDE_DOCKER_AWS_OP_REF is a 1P item reference (e.g.
# "op://claude-docker/aegon-aws") whose sub-fields are looked up by the
# canonical field names below; any trailing "/" on the ref is tolerated.
#   access_key_id     → AWS_ACCESS_KEY_ID     (required)
#   secret_access_key → AWS_SECRET_ACCESS_KEY (required)
#   session_token     → AWS_SESSION_TOKEN     (optional; usually absent
#                       for long-lived IAM-user keys, present for
#                       short-lived STS / SSO export dumps stored in 1P)
#   region            → AWS_REGION            (optional; not a secret —
#                       included so a single 1P item carries the whole
#                       account config and the user doesn't also need to
#                       set AWS_REGION on the host)
# Required fields missing → silent no-op (matches --ado/--jira behaviour).
# Region falls back to the host AWS_REGION if both are unset.
if [ "$WITH_AWS" = "1" ] && [ -z "${AWS_ACCESS_KEY_ID:-}" ] \
   && [ -n "${CLAUDE_DOCKER_AWS_OP_REF:-}" ]; then
  if command -v op >/dev/null 2>&1; then
    aws_ref="${CLAUDE_DOCKER_AWS_OP_REF%/}"
    aws_akid=$(op_read "$aws_ref/access_key_id" || true)
    aws_sak=$(op_read "$aws_ref/secret_access_key" || true)
    if [ -n "$aws_akid" ] && [ -n "$aws_sak" ]; then
      AWS_ACCESS_KEY_ID="$aws_akid"
      AWS_SECRET_ACCESS_KEY="$aws_sak"
      export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
      ENV_ARGS+=("-e" "AWS_ACCESS_KEY_ID" "-e" "AWS_SECRET_ACCESS_KEY")
      aws_st=$(op_read "$aws_ref/session_token" || true)
      if [ -n "$aws_st" ]; then
        AWS_SESSION_TOKEN="$aws_st"
        export AWS_SESSION_TOKEN
        ENV_ARGS+=("-e" "AWS_SESSION_TOKEN")
      fi
      if [ -z "${AWS_REGION:-}" ]; then
        aws_reg=$(op_read "$aws_ref/region" || true)
        if [ -n "$aws_reg" ]; then
          AWS_REGION="$aws_reg"
          export AWS_REGION
          ENV_ARGS+=("-e" "AWS_REGION")
        fi
      fi
    fi
  fi
fi

# --ado fallback: when AZURE_DEVOPS_EXT_PAT isn't pre-set on the host,
# read it from 1Password via `op read "$CLAUDE_DOCKER_ADO_OP_REF"`. Unlike
# the --gh/--glab fallbacks above, there's no CLI tool with a stable
# on-disk config to parse (ADO PATs typically live in a password manager,
# not in a tool config), so the source is opt-in via env var pointing at
# an op:// reference (e.g. CLAUDE_DOCKER_ADO_OP_REF="op://claude-docker/AzureDevOps PAT/credential").
# Silent on failure: op missing, not signed in, or item absent — the
# entrypoint simply won't inject an insteadOf rewrite for this session.
if [ "$WITH_ADO" = "1" ] && [ -z "${AZURE_DEVOPS_EXT_PAT:-}" ] \
   && [ -n "${CLAUDE_DOCKER_ADO_OP_REF:-}" ]; then
  if command -v op >/dev/null 2>&1; then
    ado_pat=$(op_read "$CLAUDE_DOCKER_ADO_OP_REF" || true)
    if [ -n "$ado_pat" ]; then
      AZURE_DEVOPS_EXT_PAT="$ado_pat"
      export AZURE_DEVOPS_EXT_PAT
      ENV_ARGS+=("-e" "AZURE_DEVOPS_EXT_PAT")
    fi
  fi
fi

# --jira fallback: when JIRA_API_TOKEN isn't pre-set on the host, read it
# from 1Password via `op read "$CLAUDE_DOCKER_JIRA_OP_REF"`. Same shape as
# the --ado fallback above — Atlassian API tokens aren't tied to a CLI
# tool with a config file on disk, so the source is opt-in via env var
# pointing at an op:// reference (e.g.
# CLAUDE_DOCKER_JIRA_OP_REF="op://SBP.DataChecks/jira/api-token"). Silent
# on failure: op missing, not signed in, or item absent — in-container
# Jira calls then fail loudly with HTTP 401, which is more debuggable
# than a half-injected token. JIRA_USER_EMAIL / JIRA_BASE_URL are
# forwarded as plain env vars (they're not secrets and Atlassian's Basic
# auth needs the email paired with the token); no op-read fallback for
# those — they're either in the host env or surfaced by the in-container
# project (e.g. its scripts/*.env file).
if [ "$WITH_JIRA" = "1" ] && [ -z "${JIRA_API_TOKEN:-}" ] \
   && [ -n "${CLAUDE_DOCKER_JIRA_OP_REF:-}" ]; then
  if command -v op >/dev/null 2>&1; then
    jira_tok=$(op_read "$CLAUDE_DOCKER_JIRA_OP_REF" || true)
    if [ -n "$jira_tok" ]; then
      JIRA_API_TOKEN="$jira_tok"
      export JIRA_API_TOKEN
      ENV_ARGS+=("-e" "JIRA_API_TOKEN")
    fi
  fi
fi

# Forward the enumerated host lists into the container so the entrypoint
# can write a `git config --system url.<host>.insteadOf` for each. When
# empty (no config / unparseable), the entrypoint defaults to the
# canonical public host.
[ -n "$gh_hosts" ]   && ENV_ARGS+=("-e" "CLAUDE_DOCKER_GITHUB_HOSTS=$gh_hosts")
[ -n "$glab_hosts" ] && ENV_ARGS+=("-e" "CLAUDE_DOCKER_GITLAB_HOSTS=$glab_hosts")

# Azure DevOps host list: no host-side config to enumerate (PATs are not
# tied to a CLI tool with a config file on disk like gh/glab), so default
# to dev.azure.com and honor CLAUDE_DOCKER_ADO_HOSTS as the override.
# Forward only when --ado is set; the entrypoint gates injection on the
# token being present, so no rewrite happens for sessions that didn't
# opt in even if the env var leaked.
if [ "$WITH_ADO" = "1" ]; then
  ado_hosts="${CLAUDE_DOCKER_ADO_HOSTS:-dev.azure.com}"
  ENV_ARGS+=("-e" "CLAUDE_DOCKER_ADO_HOSTS=$ado_hosts")
fi

# Forward host git identity so in-container `git commit` works without a
# per-invocation `-c user.email=...` dance. Non-opt-in: user.name/user.email
# are already on every public commit the user has ever made, so there is no
# credential to gate. GIT_AUTHOR_* / GIT_COMMITTER_* take precedence over
# config and are sufficient for commits; we deliberately skip signing and
# other host-specific settings (credential helpers, hooks) that wouldn't
# work in the container anyway.
if command -v git >/dev/null 2>&1; then
  if git_name=$(git config --global --get user.name 2>/dev/null) && [ -n "$git_name" ]; then
    ENV_ARGS+=("-e" "GIT_AUTHOR_NAME=$git_name" "-e" "GIT_COMMITTER_NAME=$git_name")
  fi
  if git_email=$(git config --global --get user.email 2>/dev/null) && [ -n "$git_email" ]; then
    ENV_ARGS+=("-e" "GIT_AUTHOR_EMAIL=$git_email" "-e" "GIT_COMMITTER_EMAIL=$git_email")
  fi
fi

# Surface active opt-ins in-container via CLAUDE_DOCKER_FLAGS so the statusline
# wrapper (below) can tag the session with what was actually granted. Order
# mirrors the README table so the tag reads predictably.
# --yolo is omitted intentionally: Claude Code already shows the permission
# mode in its UI, so duplicating it here would just be noise.
DOCKER_FLAGS=()
[ "$WITH_GH" = "1" ]       && DOCKER_FLAGS+=("gh")
[ "$WITH_AWS" = "1" ]      && DOCKER_FLAGS+=("aws")
[ "$WITH_GLAB" = "1" ]     && DOCKER_FLAGS+=("glab")
[ "$WITH_TFE" = "1" ]      && DOCKER_FLAGS+=("tfe")
[ "$WITH_TOFU" = "1" ]     && DOCKER_FLAGS+=("tofu")
[ "$WITH_ADO" = "1" ]      && DOCKER_FLAGS+=("ado")
[ "$WITH_JIRA" = "1" ]     && DOCKER_FLAGS+=("jira")
[ "$WITH_CLAUDE_AUTH" = "1" ] && DOCKER_FLAGS+=("auth")
[ "$EPHEMERAL" = "1" ]     && DOCKER_FLAGS+=("ephemeral")
[ "$RO_WORKSPACES" = "1" ] && DOCKER_FLAGS+=("ro")
if [ "${#DOCKER_FLAGS[@]}" -gt 0 ]; then
  old_ifs=$IFS; IFS=','; DOCKER_FLAGS_CSV="${DOCKER_FLAGS[*]}"; IFS=$old_ifs
  ENV_ARGS+=("-e" "CLAUDE_DOCKER_FLAGS=$DOCKER_FLAGS_CSV")
fi

# Host Claude config parity: mount host config items read-only into the container.
# Directories: resolve the top-level symlink so Docker gets a real path under
# /Users (which is the only host path Colima shares into its VM by default;
# Docker Desktop also shares it). The statusline wrapper is generated content
# so it still needs a real stage dir — stage that under $HOME for the same
# reason: /tmp and $TMPDIR are NOT shared by Colima's default mount config,
# so any bind-mount from those paths silently yields an empty mountpoint in
# the container. $TMPDIR on macOS is /var/folders/... (not shared by either
# runtime); /tmp is shared by Docker Desktop only.
stage_root="$HOME/.cache/claude-docker"
mkdir -p "$stage_root"
stage=$(mktemp -d "$stage_root/host.XXXXXX")
# `case` instead of `[[ ]]` for bash 3.2 friendliness inside the trap string.
# $HOME is expanded at trap execution time, * is a glob wildcard.
trap 'case "$stage" in "$HOME/.cache/claude-docker/host."*) rm -rf "$stage" ;; esac' EXIT

for item in agents commands skills; do
  src="$CLAUDE_CONFIG_DIR/$item"
  # Resolve top-level symlink so cp -RL gets a real directory path, not a link.
  # Hop counter guards against pathological symlink cycles (a -> b -> a).
  hops=0
  while [ -L "$src" ] && [ "$hops" -lt 10 ]; do
    link=$(readlink "$src")
    case "$link" in /*) src="$link" ;; *) src="$(dirname "$src")/$link" ;; esac
    hops=$((hops + 1))
  done
  if [ -d "$src" ]; then
    # cp -RL dereferences all symlinks within the tree so internal symlinks
    # (e.g. skills/foo -> ~/git/repo/skills/foo) resolve inside the container.
    cp -RL "$src" "$stage/$item"
    MOUNT_ARGS+=("-v" "$stage/$item:/root/.claude/$item:ro")
  fi
done

# Wrapper-shipped hooks: ship with the docker repo itself so every container
# spawned by this wrapper gets them, independent of the user's host .claude
# config. Activation still requires the user's settings.docker.json to wire
# the hook commands into Claude's hook events.
if [ -d "$SELF_DIR/hooks" ]; then
  cp -RL "$SELF_DIR/hooks" "$stage/hooks"
  MOUNT_ARGS+=("-v" "$stage/hooks:/root/.claude/hooks:ro")
fi
if [ -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
  MOUNT_ARGS+=("-v" "$CLAUDE_CONFIG_DIR/CLAUDE.md:/root/.claude/CLAUDE.md:ro")
fi

# Statusline: mount the host script as-is, plus a thin wrapper at the canonical
# path that prefixes a `docker:<flags>` tag when CLAUDE_DOCKER_FLAGS is set.
# The wrapper is a no-op passthrough when unset so non-claude-docker runs of
# the same file would behave identically.
if [ -f "$CLAUDE_CONFIG_DIR/statusline-command.sh" ]; then
  cat >"$stage/statusline-command.sh" <<'WRAP'
#!/bin/sh
# claude-docker wrapper — prepends active opt-in flag tag to host statusline.
input=$(cat)
body=$(printf '%s' "$input" | sh /root/.claude/statusline-command.original.sh)
if [ -n "${CLAUDE_DOCKER_FLAGS:-}" ]; then
  printf '\033[33mdocker:%s\033[0m %s' "$CLAUDE_DOCKER_FLAGS" "$body"
else
  printf '%s' "$body"
fi
WRAP
  chmod +x "$stage/statusline-command.sh"
  MOUNT_ARGS+=(
    "-v" "$CLAUDE_CONFIG_DIR/statusline-command.sh:/root/.claude/statusline-command.original.sh:ro"
    "-v" "$stage/statusline-command.sh:/root/.claude/statusline-command.sh:ro"
  )
fi
# Mount settings.docker.json read-only as a *seed* (not directly as
# settings.json): the entrypoint copies it onto a real, writable
# settings.json on every start. A read-only single-file bind mount can't be
# written or rename()'d over, so in-session settings writes — `/effort`
# above all — failed with EBUSY. The seed copy lives in the per-container
# writable layer of the claude-code-home volume, so each container's
# settings.json is independent and `/effort` changes stay local to that
# session; the on-start default always tracks this seed.
[ -f "$CLAUDE_CONFIG_DIR/settings.docker.json" ] \
  && MOUNT_ARGS+=("-v" "$CLAUDE_CONFIG_DIR/settings.docker.json:/root/.claude/settings.docker.json:ro")

# --claude-auth: share the host Claude OAuth login with the container.
# Bind-mount the host credentials file (read-write) over the path Claude
# reads inside the container. It sits "below" the claude-code-home volume
# mount (/root/.claude) by path depth, so Docker overlays it regardless of
# -v ordering — same mechanism as settings.docker.json above. RW (not :ro)
# so an in-session token refresh writes straight back to the host file,
# keeping a single source of truth and ending the host/container token
# tug-of-war that surfaces as a periodic in-container 401 / "run /login".
# Gated + off by default: it exposes the real credential to a --yolo
# container (exfil surface via a prompt-injected workspace file), so it is
# opt-in. Fails loudly if the host has never logged in.
if [ "$WITH_CLAUDE_AUTH" = "1" ]; then
  if [ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
    MOUNT_ARGS+=("-v" "$CLAUDE_CONFIG_DIR/.credentials.json:/root/.claude/.credentials.json")
  else
    echo "claude-docker: --claude-auth set but $CLAUDE_CONFIG_DIR/.credentials.json not found; run 'claude' and /login on the host first" >&2
    exit 1
  fi
fi

CMD=(claude)
# Grant claude read/write access to every mounted workspace, not just cwd.
# Index 0 is already cwd, so skip it. Repeat --add-dir is allowed; we don't
# dedupe against any user-supplied --add-dir after `--`.
n=${#CONTAINER_PATHS[@]}
i=1
while [ "$i" -lt "$n" ]; do
  CMD+=("--add-dir" "${CONTAINER_PATHS[$i]}")
  i=$((i + 1))
done
[ "${#CLAUDE_FLAGS[@]}" -gt 0 ] && CMD+=("${CLAUDE_FLAGS[@]}")
# CLAUDE_DOCKER_TMUX=1   → plain tmux (works in any terminal)
# CLAUDE_DOCKER_TMUX=cc  → tmux -CC, iTerm2 control mode (native panes on macOS).
#                          Host must NOT already be inside tmux -CC — nesting
#                          collapses the inner server to plain splits.
# Wrap claude so a fast non-zero exit (e.g. `claude -w` from a non-git dir)
# stays readable: tmux tears the pane down the moment its command exits AND
# always returns 0 itself, so without this hold the user sees neither the
# error message nor a non-zero status — the wrapper just appears to no-op.
HOLD_ON_ERR='"$@"; rc=$?; if [ $rc -ne 0 ]; then printf "\n[claude exited %d — press Enter to close] " "$rc" >&2; read -r _; fi; exit $rc'
case "${CLAUDE_DOCKER_TMUX:-0}" in
  cc|CC) CMD=(tmux -u -CC new-session -A -s claude sh -c "$HOLD_ON_ERR" _ "${CMD[@]}") ;;
  1)     CMD=(tmux -u     new-session -A -s claude sh -c "$HOLD_ON_ERR" _ "${CMD[@]}") ;;
esac

# Persistent named volumes carry OAuth tokens, gh login, conversation history.
# --ephemeral skips them for one-shot untrusted sessions. Prepend to MOUNT_ARGS
# so the docker run line has no conditionally-empty array (bash 3.2 set -u).
if [ "$EPHEMERAL" = "0" ]; then
  # Mask persisted in-container auth state when the opt-in flag is off, so a
  # prior `gh`/`glab`/`terraform`/`tofu` auth login stored under
  # claude-code-root doesn't leak into a session the user didn't ask to grant
  # those creds to. The /root/.terraform.d mask is gated on both --tfe and
  # --tofu being off: `terraform login` and `tofu login` write the same path,
  # so either flag is sufficient consent to expose it.
  [ "$WITH_GH" = "0" ]   && MOUNT_ARGS+=("--tmpfs" "/root/.config/gh")
  [ "$WITH_GLAB" = "0" ] && MOUNT_ARGS+=("--tmpfs" "/root/.config/glab-cli")
  [ "$WITH_TFE" = "0" ] && [ "$WITH_TOFU" = "0" ] && MOUNT_ARGS+=("--tmpfs" "/root/.terraform.d")
  MOUNT_ARGS=(-v claude-code-root:/root -v claude-code-home:/root/.claude "${MOUNT_ARGS[@]}")
fi

docker run --rm -it \
  --security-opt no-new-privileges \
  --cap-drop ALL \
  --cap-add DAC_OVERRIDE \
  --cap-add FOWNER \
  "${MOUNT_ARGS[@]}" \
  "${ENV_ARGS[@]}" \
  -w "$CWD" \
  "$IMAGE" \
  "${CMD[@]}"
