## Why

`add-git-insteadof` taught in-container `git` to authenticate against
private HTTPS hosts by writing, at container startup,

```
git config --system url."https://oauth2:$TOKEN@$HOST".insteadOf "https://$HOST"
```

for each opted-in host. That works for auth — but it embeds the token in
the **URL**, and git applies the `insteadOf` rewrite to the URL it prints
in nearly every URL-surfacing command: `git remote -v`, `git fetch -v`,
`git ls-remote`, `git remote prune`, and clone/push progress. So the token
leaks into the output of routine git commands, and from there into any
log, shell history, or AI-agent transcript that captures that output.

Observed in the wild: an agent ran `git remote prune origin` in a
`--glab` session and the GitLab PAT printed in clear in the transcript via
the echoed `URL:` line — even though the repo's own `.git/config` remote
was **bare** (`git config --get remote.origin.url` had no token). The
token came entirely from the `--system` `insteadOf` rewrite. The prior
change's own design flagged "token leak via git config dump / log output"
as a risk and even floated a credential helper as an alternative, but
deferred it ("Skipping unless a real workflow needs it"). Leak prevention
is that workflow.

## What Changes

- **Replace the `insteadOf` URL rewrite with a per-host git credential
  helper.** For each opted-in host the entrypoint writes:

  ```
  git config --system credential.https://<host>.username oauth2
  git config --system credential.https://<host>.helper \
    '!f() { test "$1" = get && printf "password=%s\n" "$<TOKEN_ENV_VAR>"; }; f'
  ```

  The helper reads the token from the forwarded env var **at auth time**,
  so the secret is supplied during the HTTPS handshake — never embedded in
  a URL git can echo, and never written to `/etc/gitconfig` (the stored
  helper holds only a *reference* to the env var, e.g. `$GITLAB_TOKEN`,
  not its value).
- **Everything upstream of the entrypoint is unchanged**: the same
  `--gh` / `--glab` / `--ado` opt-ins, the same `gh`/`glab auth token`
  fallbacks, the same `CLAUDE_DOCKER_{GITHUB,GITLAB,ADO}_HOSTS`
  enumeration and env-var forwarding in `run.sh`. Only the in-container
  `entrypoint.sh` injection changes.
- **Keep** the control-char guard on the token (a multi-line value would
  make the helper emit extra credential lines — a protocol-smuggling
  hazard), the `--system` scope (ephemerality argument unchanged), and
  `username=oauth2` (works for GitHub PATs, GitLab's documented `oauth2:`
  pattern, and Azure Repos PAT auth alike).
- **Update README** Auth model + Threat model wording: the token is no
  longer visible in git's URL output, and `git config --system --list` now
  shows only the helper script, not the secret.

Out of scope (unchanged from `add-git-insteadof`):
- SSH-based git auth.
- Token rotation mid-session — the forwarded env var is a launch-time
  snapshot; the helper reads it live, but a host-side rotation still needs
  a container restart to re-forward.
- `run.sh` host enumeration / forwarding — reused verbatim.

## Capabilities

### Modified Capabilities

- `external-cli-tools`: the `--gh` / `--glab` / `--ado` opt-ins inject a
  per-host **git credential helper** (reading the token from the forwarded
  env var at auth time) instead of an `url.<host>.insteadOf` URL rewrite.
  Auth coverage (clone, fetch, push, tool-spawned git) and the
  ephemerality / user-override invariants are preserved; the token no
  longer appears in git URL output or in `/etc/gitconfig`.

## Impact

- **Code**: `claude-docker/entrypoint.sh` (replace `inject_insteadof` with
  `inject_credential`; update the three call sites to pass the token's env
  expansion expression). No `run.sh` or `Dockerfile` change.
- **Docs**: `claude-docker/README.md` (Auth model rows + Threat model
  bullet reworded from URL rewrite to credential helper; note URLs stay
  bare in git output).
- **Specs**: delta to `external-cli-tools` MODIFYING the requirement
  added by `add-git-insteadof`.
- **No breaking changes.** Auth behaviour is identical from the user's
  point of view (`git clone`, `tofu init`, `go get` against opted-in hosts
  still Just Work, same flags). A user who maintains a custom
  `git config --global` (credential or insteadOf) still wins via
  precedence (`--local > --global > --system`).
- **Dependencies**: none. Uses `git` and POSIX `sh` already present.
