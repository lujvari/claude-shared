## Context

`add-git-insteadof` closed the "in-container git can't auth against
private HTTPS hosts" gap by writing `url.<host>.insteadOf` rewrites with
the token embedded as `oauth2:$TOKEN@<host>`. The auth works, but the
embedding has a side effect the prior change documented as a risk and left
unaddressed: git applies the rewrite to the URL it *prints*, not just the
URL it *connects to*. So `git remote -v`, `git fetch -v`, `git ls-remote`,
`git remote prune`, and clone/push progress all echo `oauth2:<token>@host`
— leaking the PAT into any captured output.

This is sharper than the generic "anything that dumps config leaks the
token" risk: it fires on ordinary read-only commands an agent or CI runs
constantly, against a repo whose own `.git/config` is completely clean.

The fix keeps the entire credential-delivery chain (host → WSL env →
`-e TOKEN` → container env) and changes only how the entrypoint tells git
to *use* the env var that's already there.

## Goals / Non-Goals

**Goals:**
- The token never appears in any URL git prints (`remote -v`, `fetch -v`,
  `ls-remote`, `remote prune`, clone/push progress all show bare URLs).
- The token is never written to `/etc/gitconfig` — `git config --system
  --list` exposes the helper script, not the secret.
- Identical auth coverage to `insteadOf`: clone, fetch, push, and
  tool-spawned git (`tofu init`, `go get`) against opted-in hosts.
- Zero change to the user's host, WSL `.bashrc`, 1Password setup, or
  invocation. Same flags, same UX.
- No sandbox change: no new mounts, env vars, capabilities, or network
  surface. Strictly tighter (secret leaves the config file).

**Non-Goals:**
- SSH auth, mid-session rotation, Bitbucket/Gitea — unchanged from the
  prior change.
- Reworking `run.sh` enumeration/forwarding — reused as-is.

## Decisions

### D1: Credential helper reads the env var by NAME, not value

The stored helper is `'!f() { test "$1" = get && printf "password=%s\n"
"$GITLAB_TOKEN"; }; f'`. The entrypoint substitutes only the *expression*
`$GITLAB_TOKEN` (passed single-quoted from the call site, so this shell
leaves it literal); `$1` and the `printf` format stay literal for git's
runtime shell. Git invokes the helper as `sh -c '<helper> get'` at auth
time, where it expands `$GITLAB_TOKEN` from the container environment.

Result: the token value lives **only** in the container env var (where it
already is — same blast radius as today). It is never written to
`/etc/gitconfig`.

**Alternative considered — bake the token VALUE into the helper string**
(`printf 'password=%s\n' '<literal-token>'`). Rejected: it solves the
URL-leak but re-introduces the secret into `/etc/gitconfig`, so a config
dump still leaks it, and a token containing a quote would break the
string. Reading the env var by name is strictly cleaner.

### D2: `username=oauth2` set in config, helper emits only `password`

`credential.https://<host>.username = oauth2` is written per host so git
never prompts for a username; the helper returns only `password=…`. This
matches the `oauth2:` username the prior change chose (its D3) and works
across all three forges: GitHub (PAT in the password slot, any non-empty
username), GitLab (the documented `oauth2:<token>` pattern), Azure Repos
(any username + PAT password). Verified with `git credential fill` for all
three hosts.

### D3: Per-host `credential.https://<host>` URL scoping

Each helper is scoped to its host via `credential.https://<host>.*`, so
GitHub/GitLab/ADO tokens never cross hosts (git matches credential context
by protocol+host). GitHub's helper expression is `${GH_TOKEN:-$GITHUB_TOKEN}`
to honour the same precedence the rest of the wrapper uses; GitLab uses
`$GITLAB_TOKEN`, ADO uses `$AZURE_DEVOPS_EXT_PAT`.

### D4: Keep `--system` (`/etc/gitconfig`)

Unchanged from the prior change's D1: `/etc/gitconfig` is in the
`docker run --rm` writable layer and discarded on exit, so the config
(now just a helper script, no secret) never persists via `claude-code-root`
(which mounts `/root/`, not `/etc/`). Precedence `--local > --global >
--system` still lets a user's own `/root/.gitconfig` win.

### D5: Credential helper covers push, not just clone

The prior change's open question ("insteadOf already covers push;
credential.helper redundant") had it backwards for our purpose: a
URL-scoped credential helper applies to *every* git operation that
authenticates against the host — clone, fetch, AND push — exactly like the
insteadOf rewrite did. Confirmed end-to-end: `git ls-remote` against the
real self-hosted GitLab returns refs (exit 0) with the helper and a bare
URL, no insteadOf present.

## Risks / Trade-offs

- **Risk:** token still readable in the container env
  (`/proc/<pid>/environ`, `env`) by the claude agent and its subprocesses.
  → **Mitigation:** identical to the already-forwarded env var; no
  widening. Strictly better than `insteadOf`, which *additionally* put the
  token in `/etc/gitconfig` and in git URL output.

- **Risk:** a malformed multi-line token would make the helper print extra
  lines into the credential protocol (smuggling a second key/value).
  → **Mitigation:** the control-char guard (`*[[:cntrl:]]*`) from the
  prior change is retained; it rejects and warns per host group, then
  continues startup.

- **Trade-off:** the helper is a small inline shell function rather than a
  standalone script. Kept inline to avoid shipping another file and to
  keep the token-source obvious in one place.

## Migration Plan

Purely a swap of the in-container injection mechanism. A user sees
identical auth behaviour. Rollback is reverting `entrypoint.sh` to the
`inject_insteadof` form. No image-layer or run.sh change to coordinate.

## Open Questions

- Should `git config --system --list` (which now shows the helper script
  with the literal `$GITLAB_TOKEN` reference, no value) still be redacted
  in any tooling that dumps it? It exposes no secret, so: no — but worth a
  README note so readers don't mistake the `$GITLAB_TOKEN` text for a leak.
