## 1. Container entrypoint

- [x] 1.1 Replace `inject_insteadof` with `inject_credential` in
  `claude-docker/entrypoint.sh`: for each host write `git config --system
  credential.https://<host>.username oauth2` and a `.helper` inline sh
  function that prints `password=%s` reading the token from the env var at
  auth time.
- [x] 1.2 Take a third arg (`tok_expr`) = the literal env-var expansion the
  helper embeds (`$GITLAB_TOKEN`, `${GH_TOKEN:-$GITHUB_TOKEN}`,
  `$AZURE_DEVOPS_EXT_PAT`); pass it single-quoted from each call site so the
  entrypoint shell leaves it unexpanded.
- [x] 1.3 Keep the `*[[:cntrl:]]*` control-char guard (multi-line token →
  helper would emit extra credential lines); keep the `[ -n "$tok" ]` /
  `[ -n "$hosts" ]` no-op guards and `set -eu`.
- [x] 1.4 Update the entrypoint header comment to describe the
  credential-helper mechanism and the URL-leak rationale.

## 2. Verification (done in-session, pre-commit)

- [x] 2.1 Stored config has NO token value — only the `$ENV_VAR` reference
  (asserted: `grep` for the fake token value in the generated `--system`
  config returns nothing).
- [x] 2.2 `git credential fill` returns `username=oauth2` + the live env
  var value for each of the three hosts (GitLab, GitHub, ADO).
- [x] 2.3 GitHub `${GH_TOKEN:-$GITHUB_TOKEN}` precedence verified: falls
  back to `GITHUB_TOKEN` when `GH_TOKEN` is unset.
- [x] 2.4 End-to-end against the real self-hosted GitLab: with system
  config nulled + the credential helper via `-c`, `git ls-remote
  https://sbp.gitlab.schubergphilis.com/<repo> HEAD` returns the HEAD sha
  (exit 0) and the URL stays bare.

## 3. Documentation

- [ ] 3.1 Reword the `--gh` / `--glab` / `--ado` Auth model rows in
  `README.md`: the forwarded token now drives a per-host git *credential
  helper* (not an `insteadOf` URL rewrite); the token stays out of git URL
  output and out of `/etc/gitconfig`.
- [ ] 3.2 Update the "Private git module fetch" subsection to match
  (credential helper, bare URLs, env-var-read-at-auth-time).
- [ ] 3.3 Update the Threat model bullet: `--gh`/`--glab` make the token
  available to in-container git via a credential helper that reads the
  forwarded env var — same blast radius as the env var, and (unlike the
  prior insteadOf) the secret no longer appears in git URL output or in a
  `git config --system --list` dump (only the `$ENV_VAR` reference does).

## 4. Image smoke tests (host-side, needs docker)

- [ ] 4.1 `docker build -t claude-code:local ./claude-docker` succeeds.
- [ ] 4.2 No-flag invariant: `docker run --rm claude-code:local sh -c
  'git config --system --list | grep credential || echo none'` prints
  `none`.
- [ ] 4.3 `--glab` with token: `docker run --rm -e GITLAB_TOKEN=glpat_fake
  claude-code:local sh -c 'git config --system --get
  credential.https://gitlab.com.helper'` shows a helper referencing
  `$GITLAB_TOKEN`, and `... | grep glpat_fake` finds nothing.
- [ ] 4.4 No URL rewrite present: same container, `git config --system
  --get-all url.https://gitlab.com.insteadOf` prints nothing.
- [ ] 4.5 No-leak across exits: a follow-up no-flag `docker run --rm
  claude-code:local sh -c 'git config --system --list'` shows no
  `credential.*` entries.
- [ ] 4.6 End-to-end: `claude-docker --glab ~/repo`, then in-container
  `git remote -v` / `git fetch -v` show bare URLs (no `oauth2:…@`), and a
  private clone / `tofu init` against an SBP GitLab module source succeeds.

## 5. Validation

- [ ] 5.1 `openspec validate use-git-credential-helper --strict` exits 0.
- [ ] 5.2 `claude-docker --help` round-trips unchanged (no new flags).
- [ ] 5.3 Archive `add-git-insteadof` is left intact; this change MODIFIES
  its requirement rather than re-adding one.
