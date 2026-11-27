## 1. Container entrypoint

- [x] 1.1 Create `claude-docker/entrypoint.sh` — POSIX `sh`, no bashisms; reads `GH_TOKEN` / `GITHUB_TOKEN` and `GITLAB_TOKEN`, plus `CLAUDE_DOCKER_GITHUB_HOSTS` / `CLAUDE_DOCKER_GITLAB_HOSTS` (defaults: `github.com` / `gitlab.com`); writes `git config --system url."https://oauth2:$TOKEN@$HOST.insteadOf" "https://$HOST"` for each authenticated host; then `exec "$@"`
- [x] 1.2 Add `set -eu` to the entrypoint; guard each token block with `[ -n "$TOK" ]` so missing-token paths are no-ops, not errors; ensure non-zero exit only when `exec "$@"` itself fails
- [x] 1.3 Reject tokens with embedded control chars (`*[[:cntrl:]]*`) before passing them to `git config --system`; print a host-scoped warning to stderr and no-op that host group, then continue startup. Failure mode caught: a broken host-side capture (e.g. `export GITLAB_TOKEN="$(glab auth token 2>/dev/null)"` on a glab version where `auth token` is an unknown subcommand and prints help to stdout) would otherwise produce an opaque `git config error: invalid key (newline)` mid-startup.

## 2. Dockerfile

- [x] 2.1 `COPY entrypoint.sh /usr/local/bin/claude-docker-entrypoint` and `RUN chmod +x /usr/local/bin/claude-docker-entrypoint`, placed AFTER the tmux conf RUN block (so edits to the entrypoint script don't invalidate heavier upstream layers)
- [x] 2.2 Add `ENTRYPOINT ["/usr/local/bin/claude-docker-entrypoint"]` (keep `CMD ["claude"]` unchanged so `docker run image` semantics for non-claude-docker users remain identical)

## 3. run.sh

- [x] 3.2 Add a `_extract_hosts_from_gh()` helper that reads `~/.config/gh/hosts.yml` and prints comma-separated top-level keys (these are hostnames); silent and empty-output on missing/unparseable file
- [x] 3.3 Add a `_extract_hosts_from_glab()` helper that reads `~/.config/glab-cli/config.yml` and prints comma-separated keys under the `hosts:` section; silent and empty-output on missing/unparseable file
- [x] 3.4 When `--gh` is set, run the helper and (if non-empty) append `-e CLAUDE_DOCKER_GITHUB_HOSTS=<csv>` to `ENV_ARGS`; entrypoint will default to `github.com` when the env is absent
- [x] 3.5 Same shape for `--glab` and `CLAUDE_DOCKER_GITLAB_HOSTS`

## 6. Validation

- [x] 6.1 `openspec validate add-git-insteadof --strict` exits 0

## 7. Archive

- [ ] 7.1 Archive together with `use-git-credential-helper`, this change first: that change MODIFIES the insteadOf requirement this one ADDS, so archiving this one alone would merge a requirement that no longer holds into `openspec/specs/`. Run `openspec archive add-git-insteadof -y && openspec archive use-git-credential-helper -y` once the other change's 4.x checks are done, then `openspec validate --all`.
