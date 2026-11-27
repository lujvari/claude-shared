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

- [x] 3.1 Reword the `--gh` / `--glab` / `--ado` Auth model rows in
  `README.md`: the forwarded token now drives a per-host git *credential
  helper* (not an `insteadOf` URL rewrite); the token stays out of git URL
  output and out of `/etc/gitconfig`.
- [x] 3.2 Update the "Private git module fetch" subsection to match
  (credential helper, bare URLs, env-var-read-at-auth-time).
- [x] 3.3 Update the Threat model bullet: `--gh`/`--glab` make the token
  available to in-container git via a credential helper that reads the
  forwarded env var — same blast radius as the env var, and (unlike the
  prior insteadOf) the secret no longer appears in git URL output or in a
  `git config --system --list` dump (only the `$ENV_VAR` reference does).

## 4. Image smoke tests (host-side, needs docker)

- [x] 4.1 `docker build -t claude-code:local ./claude-docker` succeeds.
- [ ] 4.2 No flag: `docker run --rm claude-code:local sh -c 'git config --list | grep credential || echo none'`. Pass: prints `none`. Use `--list`, not `--system`: the helper lives in `/tmp/claude-docker-gitconfig`, included from `/etc/gitconfig`, and `--system` does not follow includes.
- [ ] 4.3 `docker run --rm -e GITLAB_TOKEN=glpat_fake claude-code:local sh -c 'git config --get credential.https://gitlab.com.helper; git config --list | grep -c glpat_fake'`. Pass: the helper line references `$GITLAB_TOKEN`, and the count is 0.
- [ ] 4.4 Same container as 4.3: `git config --get-all url.https://gitlab.com.insteadOf; echo rc=$?`. Pass: prints nothing, then `rc=1`.
- [ ] 4.5 After 4.3, a fresh no-flag `docker run --rm claude-code:local sh -c 'git config --list | grep -c credential'`. Pass: 0.
- [ ] 4.6 `claude-docker --glab <repo>`, then `git remote -v` (bare https URLs, no token), `git fetch -v` and a private clone of an SBP GitLab repo. Pass: URLs are bare and fetch and clone succeed.

## 5. Validation

- [x] 5.1 `openspec validate use-git-credential-helper --strict` exits 0.
- [x] 5.2 `claude-docker --help` round-trips unchanged (no new flags).
- [ ] 5.3 At archive time: archive `add-git-insteadof` first (see its 7.1), then this change; check `git log -- openspec/changes/archive/*add-git-insteadof*` shows the archived folder unchanged by this archive.
