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
# even lands in /etc/gitconfig (the helper holds only a reference to the
# env var, not its value).
#
# Writes /etc/gitconfig (--system), NOT /root/.gitconfig (--global), so the
# config is gone with the writable layer on `docker run --rm` exit — never
# persists via the claude-code-root named volume. Precedence:
# --local > --global > --system, so a user's own /root/.gitconfig entry
# wins, preserving user intent.
set -eu

# claude-code native binary lives at /opt/claude-code/claude (image layer,
# survives volume masking on bump). The binary self-checks for itself at
# /root/.local/bin/claude — wire that symlink up here so it always points
# to the current image's binary regardless of what the claude-code-root
# named volume has cached from a prior image. `-f` overwrites any stale
# regular file or symlink left there by an earlier `claude install`.
if [ -x /opt/claude-code/claude ]; then
  mkdir -p /root/.local/bin
  ln -sf /opt/claude-code/claude /root/.local/bin/claude
fi

# Inject a git credential helper for each host in a CSV list. The helper
# runs at auth time and reads the token from the named env var, so the
# secret is supplied during the HTTPS handshake and never appears in a URL
# or in /etc/gitconfig.
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
    git config --system "credential.https://${host}.username" "oauth2"
    git config --system "credential.https://${host}.helper" \
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

# Per-container writable settings. run.sh bind-mounts settings.docker.json
# read-only as a *seed* at /root/.claude/settings.docker.json; copy it onto
# the real settings.json on every start. This makes settings.json a plain
# writable file in the claude-code-home volume (a read-only single-file bind
# mount can't be rename()'d over, which is how `/effort` and other in-session
# settings writes persist — that's the EBUSY they hit). Copying on every
# start means the on-start default tracks the seed and a live `/effort`
# change applies to that session only, so it never leaks across the other
# containers sharing this volume.
if [ -f /root/.claude/settings.docker.json ]; then
  cp -f /root/.claude/settings.docker.json /root/.claude/settings.json
fi

# `exec` so signals (Ctrl-C in tmux, container stop) reach claude/tmux
# directly without an extra shell hop intercepting them.
exec "$@"
