#!/bin/sh
# claude-docker-entrypoint: teach in-container `git` to authenticate
# against the same private HTTPS hosts the matching CLI tool (`gh` / `glab`
# / `az devops`) was opted in for, so clones and tool-spawned git fetches
# (tofu/terraform init, go get) Just Work. See
# openspec/changes/use-git-credential-helper/ (supersedes the original
# insteadOf approach in add-git-insteadof/).
#
# Mechanism: a per-host git credential helper (--system) that reads the
# token from the forwarded env var AT AUTH TIME. We deliberately do NOT
# embed oauth2:$TOKEN@host into the URL via `url.<host>.insteadOf`: git
# echoes the rewritten URL into the output of nearly every URL-printing
# command (git remote -v, fetch -v, ls-remote, remote prune, clone/push
# progress), so insteadOf leaks the token into any transcript or log that
# captures git output. The credential helper supplies the secret during the
# HTTPS handshake instead — URLs stay bare everywhere, and the token never
# even lands in a git config file (the helper holds only a reference to the
# env var, not its value).
#
# Writes $GIT_RUNTIME_CONFIG, which /etc/gitconfig includes (the Dockerfile
# wires the include.path; the runtime user can't write /etc/gitconfig itself).
# It sits in /tmp, so the config is gone with the writable layer on
# `docker run --rm` exit — never persists via the claude-code-root named
# volume. Being included from the system file, it keeps --system precedence:
# --local > --global > --system, so a user's own ~/.gitconfig entry wins,
# preserving user intent.
set -eu

GIT_RUNTIME_CONFIG=/tmp/claude-docker-gitconfig
: > "$GIT_RUNTIME_CONFIG"

# Fail with the fix, not a bare EACCES, when part of $HOME is still owned by
# root from the days boxes ran as uid 0 (or was created as root by Docker as a
# mountpoint parent). The one-off volume chown in the README fixes it.
need_writable_dir() {
  mkdir -p "$1" 2>/dev/null || true
  if [ ! -w "$1" ]; then
    echo "claude-docker-entrypoint: $1 is not writable by uid $(id -u); the claude-code-root volume predates the non-root image. Run the one-off volume migration in claude-docker/README.md." >&2
    exit 1
  fi
}

# claude-code native binary lives at /opt/claude-code/claude (image layer,
# survives volume masking on bump). The binary self-checks for itself at
# ~/.local/bin/claude — wire that symlink up here so it always points
# to the current image's binary regardless of what the claude-code-root
# named volume has cached from a prior image. `-f` overwrites any stale
# regular file or symlink left there by an earlier `claude install`.
if [ -x /opt/claude-code/claude ]; then
  need_writable_dir "$HOME/.local/bin"
  ln -sf /opt/claude-code/claude "$HOME/.local/bin/claude"
fi

# --aws static credentials → named profile in ~/.aws/credentials.
# run.sh hands static IAM keys to the container under CLAUDE_DOCKER_AWS_STATIC_*
# transport vars (NOT as ambient AWS_ACCESS_KEY_ID, which would outrank the
# mounted SSO profile and any --profile-less call). Materialize them here under
# a named profile so tenants are selected explicitly with --profile and there
# is no silent default identity. ~/.aws/config is bind-mounted :ro; the parent
# dir and ~/.aws/credentials are ours to write (run.sh never mounts creds).
# Transport vars are unset afterwards so the secret does not linger in the
# environment `exec`'d into claude.
if [ -n "${CLAUDE_DOCKER_AWS_STATIC_KEY_ID:-}" ] \
   && [ -n "${CLAUDE_DOCKER_AWS_STATIC_SECRET:-}" ]; then
  aws_profile="${CLAUDE_DOCKER_AWS_STATIC_PROFILE:-aegon}"
  need_writable_dir "$HOME/.aws"
  {
    printf '[%s]\n' "$aws_profile"
    printf 'aws_access_key_id = %s\n' "$CLAUDE_DOCKER_AWS_STATIC_KEY_ID"
    printf 'aws_secret_access_key = %s\n' "$CLAUDE_DOCKER_AWS_STATIC_SECRET"
    if [ -n "${CLAUDE_DOCKER_AWS_STATIC_TOKEN:-}" ]; then
      printf 'aws_session_token = %s\n' "$CLAUDE_DOCKER_AWS_STATIC_TOKEN"
    fi
    if [ -n "${CLAUDE_DOCKER_AWS_STATIC_REGION:-}" ]; then
      printf 'region = %s\n' "$CLAUDE_DOCKER_AWS_STATIC_REGION"
    fi
  } > "$HOME/.aws/credentials"
  chmod 600 "$HOME/.aws/credentials"
fi
unset CLAUDE_DOCKER_AWS_STATIC_KEY_ID CLAUDE_DOCKER_AWS_STATIC_SECRET \
      CLAUDE_DOCKER_AWS_STATIC_TOKEN CLAUDE_DOCKER_AWS_STATIC_REGION \
      CLAUDE_DOCKER_AWS_STATIC_PROFILE 2>/dev/null || true

# Inject a git credential helper for each host in a CSV list. The helper
# runs at auth time and reads the token from the named env var, so the
# secret is supplied during the HTTPS handshake and never appears in a URL
# or in any git config file.
#
# Args:
#   $1 tok       — resolved token VALUE, used ONLY for the present/valid
#                  guards below; never written to config.
#   $2 hosts     — comma-separated host list.
#   $3 tok_expr  — POSIX-sh expansion the helper uses to read the live token
#                  at auth time, e.g. '$GITLAB_TOKEN'. Pass it single-quoted
#                  so THIS shell leaves it unexpanded and the literal text
#                  lands in the helper.
# No-op on empty token or empty host list — the no-opt-in case where this
# script should be invisible.
inject_credential() {
  tok=$1
  hosts=$2
  tok_expr=$3
  [ -n "$tok" ] || return 0
  [ -n "$hosts" ] || return 0
  # Reject tokens with embedded control chars (newlines, tabs, CR).
  # Real PATs/OAuth tokens are single-line printable ASCII; control
  # chars almost always mean the host-side source is broken — most
  # commonly `export GITLAB_TOKEN="$(glab auth token 2>/dev/null)"`
  # in ~/.bashrc, where `glab auth token` is an unknown subcommand
  # on the user's glab version and prints help to stdout. A multi-line
  # value would make the helper emit extra credential lines (a
  # protocol-smuggling hazard); warn with a host hint so the user can
  # locate the offending env var, then no-op this host group.
  case $tok in
    *[[:cntrl:]]*)
      echo "claude-docker-entrypoint: token for hosts '$hosts' contains control characters; skipping git credential injection. Check the env var that exported this token on the host." >&2
      return 0
      ;;
  esac
  # POSIX field-splitting on comma; for-loop avoids the
  # `while read` pipeline subshell whose set -e semantics differ
  # across dash/bash. Save/restore IFS so we don't perturb callers.
  old_ifs=$IFS
  IFS=','
  for host in $hosts; do
    [ -n "$host" ] || continue
    # username=oauth2 works for GitHub (PAT in password slot, any non-empty
    # user), GitLab (documented oauth2: pattern), and Azure Repos (any user
    # + PAT password). Helper emits only the password, read live from the
    # env var; ${tok_expr} is substituted by THIS shell into the stored
    # string, while \$1 / the printf format stay literal for git's runtime.
    git config --file "$GIT_RUNTIME_CONFIG" "credential.https://${host}.username" "oauth2"
    git config --file "$GIT_RUNTIME_CONFIG" "credential.https://${host}.helper" \
      "!f() { test \"\$1\" = get && printf \"password=%s\n\" \"${tok_expr}\"; }; f"
  done
  IFS=$old_ifs
}

# GH_TOKEN takes precedence over GITHUB_TOKEN (matches gh's own
# precedence rule). Default host is github.com when
# CLAUDE_DOCKER_GITHUB_HOSTS is absent — covers the public-only case
# when host enumeration found nothing.
gh_tok="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
inject_credential "$gh_tok" "${CLAUDE_DOCKER_GITHUB_HOSTS:-github.com}" '${GH_TOKEN:-$GITHUB_TOKEN}'

# GITLAB_TOKEN is the env var glab and the GitLab API both honour;
# no GITHUB_TOKEN-style synonym to pick between.
inject_credential "${GITLAB_TOKEN:-}" "${CLAUDE_DOCKER_GITLAB_HOSTS:-gitlab.com}" '$GITLAB_TOKEN'

# AZURE_DEVOPS_EXT_PAT is the env var the `az devops` extension honours.
# Azure Repos HTTPS auth accepts any non-empty username paired with a PAT
# as the password, so the same `oauth2:<tok>@<host>` shape used for
# gh/glab works unchanged here. CLAUDE_DOCKER_ADO_HOSTS defaults to
# dev.azure.com in run.sh; legacy `*.visualstudio.com` hosts are out of
# scope unless the user sets the override explicitly.
inject_credential "${AZURE_DEVOPS_EXT_PAT:-}" "${CLAUDE_DOCKER_ADO_HOSTS:-dev.azure.com}" '$AZURE_DEVOPS_EXT_PAT'

# Writable settings. run.sh bind-mounts settings.docker.json read-only as a
# *seed* at ~/.claude/settings.docker.json; copy it onto the real
# settings.json on every start. This makes settings.json a plain writable
# file (a read-only single-file bind mount can't be rename()'d over, which is
# how `/effort` and other in-session settings writes persist — that's the
# EBUSY they hit).
#
# The file is SHARED, not per-container: settings.json sits on the
# claude-code-home volume, which every non-ephemeral container mounts at
# ~/.claude. So each container start resets it to the seed for all
# running containers, and a live `/effort` change is seen by any container's
# next `claude` start. Only --ephemeral containers get their own copy.
# Accepted as is. Ways to make it per-container that do NOT work:
#   - a per-container file bind-mounted over settings.json: EBUSY again;
#   - settings.json as a symlink to a per-container path: Claude Code
#     (checked in 2.1.304) refuses to write settings through a symlink, so
#     `/effort` would fail outright.
# The remaining route is a per-container CLAUDE_CONFIG_DIR with the shared
# state linked back in. It was judged too fragile, because Claude Code also
# refuses to write into symlinked directories.
if [ -f "$HOME/.claude/settings.docker.json" ]; then
  need_writable_dir "$HOME/.claude"
  cp -f "$HOME/.claude/settings.docker.json" "$HOME/.claude/settings.json"
fi

# Remote Brain MCP (--brain). User scope lives in ~/.claude.json, which is on
# the shared claude-code-root volume, so the entry holds only ${VAR}
# placeholders and Claude Code expands them at connect time (header expansion
# checked in 2.1.304). It is added once and never removed. A box without
# --brain still sees the entry, warns about missing variables and gets a 403,
# but removing the entry would break other boxes running at the same time. The
# write goes through `claude mcp` so Claude Code's own writer touches the file.
# A failure here only warns: the box still starts, just without Brain.
if [ -n "${BRAIN_CF_ACCESS_CLIENT_ID:-}" ] && [ -n "${BRAIN_CF_ACCESS_CLIENT_SECRET:-}" ] \
   && ! jq -e '.mcpServers.brain' "$HOME/.claude.json" >/dev/null 2>&1; then
  # Single quotes on purpose: the placeholders must reach the file unexpanded.
  brain_mcp='{"type":"http","url":"https://brain.karansjet.dev/mcp","headers":{"CF-Access-Client-Id":"${BRAIN_CF_ACCESS_CLIENT_ID}","CF-Access-Client-Secret":"${BRAIN_CF_ACCESS_CLIENT_SECRET}"}}'
  claude mcp add-json --scope user brain "$brain_mcp" >/dev/null 2>&1 \
    || echo "claude-docker: could not add the brain MCP entry; Brain is unavailable in this box" >&2
fi

# `exec` so signals (Ctrl-C in tmux, container stop) reach claude/tmux
# directly without an extra shell hop intercepting them.
exec "$@"
