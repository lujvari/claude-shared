## 1. run.sh

- [x] 1.1 Initialize `WITH_JIRA=0` next to the other opt-in flags
- [x] 1.2 Add `--jira` to the help heredoc with a one-line description
- [x] 1.3 Add `--jira) WITH_JIRA=1 ;;` to the flag-parsing case statement
- [x] 1.4 Append `JIRA_USER_EMAIL`, `JIRA_BASE_URL`, `JIRA_API_TOKEN` to `ENV_VARS` when `WITH_JIRA=1` so the existing forwarding loop picks them up only when set on the host
- [x] 1.5 When `--jira` is set, `JIRA_API_TOKEN` is unset on the host, and `CLAUDE_DOCKER_JIRA_OP_REF` is set, run `op read "$CLAUDE_DOCKER_JIRA_OP_REF"` and forward the result as `JIRA_API_TOKEN` (mirrors the `--ado` fallback exactly; silent on missing `op` / sign-out / item absence)
- [x] 1.6 Append `"jira"` to `DOCKER_FLAGS` when `WITH_JIRA=1` so the statusline tag surfaces it

## 2. entrypoint.sh

- [x] 2.1 No changes. Jira is a REST API, not a git host, so no `inject_insteadof` call is added. The forwarded env vars are read directly by in-container scripts (e.g. `scripts/create_deploy_ticket.py` in SBP.DataChecks).

## 3. Smoke tests

- [ ] 3.1 `docker build -t claude-code:local ./claude-docker` succeeds (no Dockerfile changes — sanity rebuild only)
- [ ] 3.2 `--jira` with explicit env: `JIRA_API_TOKEN=fake JIRA_USER_EMAIL=a@b.c JIRA_BASE_URL=https://x.atlassian.net claude-docker --jira ~/repo` → inside the container `env | grep ^JIRA_` lists all three with the host values
- [ ] 3.3 `--jira` with op-read fallback: on a host with `op` signed in to a service account that can read `op://SBP.DataChecks/jira/api-token`, `CLAUDE_DOCKER_JIRA_OP_REF=op://SBP.DataChecks/jira/api-token JIRA_USER_EMAIL=a@b.c JIRA_BASE_URL=https://x.atlassian.net claude-docker --jira ~/repo` → inside the container `echo $JIRA_API_TOKEN` is non-empty
- [ ] 3.4 No-flag invariant unchanged: `claude-docker ~/repo` without `--jira` does not export `JIRA_API_TOKEN`/`JIRA_USER_EMAIL`/`JIRA_BASE_URL` into the container even if all three are set on the host
- [ ] 3.5 Statusline tag surfaces: `claude-docker --jira ~/repo` prints `docker:jira` (or `docker:gh,jira` when combined) in the prepended status fragment
- [ ] 3.6 No `/etc/gitconfig` write: under `--jira` alone, `git config --system --list` inside the container contains no `url.*.insteadOf` entries (proves no accidental insteadOf injection)
- [ ] 3.7 End-to-end: with all three host env vars set to real values, `bash scripts/run.sh python3 scripts/create_deploy_ticket.py acceptance --dry-run` from inside `sbp/ct/SBP.DataChecks` prints the dry-run payload (requires the repo's `scripts/run.sh` short-circuit when JIRA env vars are pre-set — see Change B in the SBP.DataChecks repo)

## 4. Documentation

- [x] 4.1 Add `--jira` row to the Credential opt-in table in README
- [x] 4.2 Add `--jira` row to the Auth model table in README
- [x] 4.3 Extend the Threat model "Exposed" bullet to mention `JIRA_API_TOKEN`
- [x] 4.4 Add `jira` to the example statusline-tag list

## 5. Validation

- [ ] 5.1 `openspec validate add-jira-support --strict` exits 0
- [x] 5.2 `claude-docker --help` shows `--jira` in the flag list
- [x] 5.3 Spot-check that the `--ephemeral` interaction is a no-op: `--jira` only sets env vars and adds a statusline tag, neither of which touch the named volumes, so `--jira --ephemeral` is functionally identical to `--jira` on a fresh host except for OAuth/history persistence (orthogonal to credentials).
