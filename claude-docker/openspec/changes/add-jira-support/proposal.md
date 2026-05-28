## Why

Developers using claude-docker increasingly hit projects whose
operational workflows want in-container access to Atlassian Jira Cloud —
creating change tickets at deploy time, adding work items, attaching
test results to stories. Today the wrapper has no way to grant
in-container scripts access to Jira: `--gh` / `--glab` / `--ado` cover
git forges, `--tfe` / `--tofu` cover Terraform Cloud, but Atlassian
tokens (the email + API-token pair Jira REST uses for Basic auth) are
not forwarded and any in-container `curl -u ...` against
`*.atlassian.net` fails with HTTP 401.

Real failure mode observed in `sbp/ct/SBP.DataChecks` (BNPP EU branch's
data validation platform): the repo ships `scripts/create_deploy_ticket.py`,
a stdlib-only Python script that creates a Jira Change ticket from the
git commit list. The repo's own `scripts/run.sh` wraps the call in
`op run --env-file=scripts/deploy-ticket.env -- python3 ...` so secrets
resolve from 1Password at runtime, never to disk. That wrapper works on
the host (`op` is signed in via a service-account token in the OS
keychain) but fails inside `claude-code:local` — the image ships no
1Password CLI and has no `OP_SERVICE_ACCOUNT_TOKEN`. Today the user's
only workaround is to leave the container and run the script on the
host, which loses the in-loop "Claude drafts a payload, validates it,
then issues it" workflow this script was built to support.

A second gap, same as `--ado`: there is no Atlassian CLI tool that
stores the API token in a stable file-system path that could be bind-
mounted in. The `acli` and `jira-cli` tools each use their own config
schema (and many users skip them entirely in favour of `op://`-resolved
env vars). Env-var forwarding is the only reliable surface here — there
is no analogue of the `gh auth token` host fallback.

A third asymmetry vs `--ado`: Jira REST Basic auth requires three
values, not one. The email and the site URL are not secrets but are
required to issue any request. Forwarding only the token would make the
flag almost useless in practice; forwarding all three keeps the
in-container scripts purely env-driven.

## What Changes

- **Add `--jira` opt-in flag** to `run.sh` that forwards three
  environment variables from the host when set:
  `JIRA_USER_EMAIL`, `JIRA_BASE_URL`, and `JIRA_API_TOKEN`. Same shape
  as `--gh`/`--glab`/`--ado`: no flag → none of the three reach the
  container.
- **1Password fallback for `JIRA_API_TOKEN`** mirroring `--ado`: when
  `JIRA_API_TOKEN` is unset and `CLAUDE_DOCKER_JIRA_OP_REF` is set to
  an `op://` reference (e.g.
  `op://SBP.DataChecks/jira/api-token`), `run.sh` SHALL run
  `op read "$CLAUDE_DOCKER_JIRA_OP_REF"` on the host and forward the
  resolved value as `JIRA_API_TOKEN`. Silent on failure (op missing,
  not signed in, item absent) — in-container Jira calls then fail with
  a clear HTTP 401, which is more debuggable than a half-injected
  token. **No** op-read fallback for `JIRA_USER_EMAIL` /
  `JIRA_BASE_URL`: they are not secrets, and projects typically already
  surface them via their own `.env` files. The user either exports them
  on the host or sources them in-container from the project layer.
- **Add the `jira` tag to `CLAUDE_DOCKER_FLAGS`** so the statusline
  surfaces it like the other opt-ins.
- **No git `insteadOf` injection.** Unlike `--gh` / `--glab` / `--ado`,
  Jira is a REST API, not a git host. The entrypoint's `inject_insteadof`
  helper is not extended for this flag.
- **No Dockerfile changes.** The image already ships Python 3 (via the
  base Ubuntu install) and `curl`, which is the entire runtime any in-
  container Jira REST script needs. No CLI tool is bundled — the
  existing tools landscape (acli, jira-cli, raw curl, stdlib Python) is
  too fragmented to pick a default that wouldn't be wrong for half of
  users. Projects ship whichever script they prefer.
- **Update README** to add the `--jira` row to the credential opt-in
  table, the auth-model table, the threat-model "Exposed" bullet
  (`JIRA_API_TOKEN`), and the statusline-tag list.

Out of scope (deliberately):

- Bundling a Jira CLI tool. See above — no clear default; raw REST +
  the host project's chosen wrapper is the lowest-friction surface.
- Server / Data Center variants. Self-hosted Jira deployments use
  different auth schemes (PAT bearer tokens, or full session auth)
  and different URL structures. Users on those can still set
  `JIRA_API_TOKEN` to whatever their deployment accepts; the flag is
  agnostic about the token format because it never inspects it.
- Forwarding additional Atlassian product credentials (Confluence,
  Bitbucket Cloud). Atlassian Cloud uses the same email + API-token
  pair across products, so `--jira` already covers Confluence Cloud
  scripts that happen to live in the same repo; Bitbucket Cloud git
  auth would be a separate flag analogous to `--ado` (HTTPS + insteadOf
  injection).
- An op-read fallback for `JIRA_USER_EMAIL` / `JIRA_BASE_URL`. They are
  not secrets — putting them through 1Password is the wrong tool. If a
  project needs them surfaced in-container, the project's own env file
  is the right place.

## Capabilities

### New Capabilities

None. This change extends an existing capability.

### Modified Capabilities

- `external-cli-tools`: adds the `--jira` opt-in flag (env-var
  forwarding for the three Jira REST inputs plus an `op read` fallback
  for the token alone). The "credentials opt-in" invariant is preserved
  — the new behaviour only fires when the flag is set, and no Jira
  credentials reach the container without it.

## Impact

- **Code**: `claude-docker/run.sh` (parse `--jira`, forward the three
  env vars, op-read fallback for the token, tag statusline).
- **Docs**: `claude-docker/README.md` (credential opt-in row, auth
  model row, threat-model bullet, statusline-tag list).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.** Existing flags and defaults unchanged;
  `--jira` is purely additive and gated.
- **Dependencies**: no new binaries. The image already has Python 3
  (stdlib) and `curl` which is all a Jira REST caller needs.
