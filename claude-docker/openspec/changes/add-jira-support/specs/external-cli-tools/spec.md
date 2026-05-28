## MODIFIED Requirements

### Requirement: Credentials opt-in

Host credentials (files or env vars) SHALL NOT reach the container unless the user explicitly opts in per-run. `run.sh` defaults to no credential mounts and no token env forwarding. Opt-ins are granted via dedicated flags:

- `--aws`: mount `~/.aws/config` at `/root/.aws/config:ro` and, when present, `~/.aws/sso/` at `/root/.aws/sso:ro`; forward `AWS_PROFILE`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` when set on the host.
- `--gh`: forward `GH_TOKEN` or `GITHUB_TOKEN` when set on the host. If neither
  is set, `run.sh` SHALL attempt to retrieve the active token by running
  `gh auth token` on the host and forward the result as `GH_TOKEN`. If `gh` is
  not on the host PATH or the command fails, `run.sh` SHALL continue silently
  without a token.
- `--glab`: mount the platform-appropriate glab config dir — `~/Library/Application Support/glab-cli` on macOS, `~/.config/glab-cli` on Linux — at `/root/.config/glab-cli:ro`; forward `GITLAB_TOKEN` when set on the host.
- `--tfe`: when present on the host, mount `~/.terraform.d/credentials.tfrc.json` at `/root/.terraform.d/credentials.tfrc.json:ro`; forward `TF_TOKEN_app_terraform_io` when set on the host. Targets `app.terraform.io` (HCP Terraform); self-hosted Terraform Enterprise hostnames and other `TF_TOKEN_<host>` variables are out of scope for this opt-in.
- `--ado`: forward `AZURE_DEVOPS_EXT_PAT` when set on the host. No bind mount: Azure DevOps does not ship a CLI-tool config file at a stable cross-platform path with a parseable PAT field, so env-var forwarding is the only surface. `run.sh` SHALL forward `CLAUDE_DOCKER_ADO_HOSTS` (comma-separated host list, default `dev.azure.com`) so the entrypoint can apply git `insteadOf` rewrites to each configured Azure DevOps host. Self-hosted Azure DevOps Server and legacy `*.visualstudio.com` URLs are supported via that override; no automatic enumeration.
- `--jira`: forward `JIRA_USER_EMAIL`, `JIRA_BASE_URL`, and `JIRA_API_TOKEN` when set on the host. No bind mount: Atlassian Cloud does not ship a CLI-tool config file at a stable cross-platform path with a parseable API-token field, so env-var forwarding is the only surface. When `JIRA_API_TOKEN` is unset on the host and `CLAUDE_DOCKER_JIRA_OP_REF` is set to an `op://` reference, `run.sh` SHALL run `op read "$CLAUDE_DOCKER_JIRA_OP_REF"` on the host and forward the resolved value as `JIRA_API_TOKEN`; on `op` missing / sign-out / item-absent, `run.sh` SHALL continue silently. `JIRA_USER_EMAIL` and `JIRA_BASE_URL` are not secrets and have no `op read` fallback. Unlike `--gh` / `--glab` / `--ado`, no git `insteadOf` rewrite SHALL be injected for this flag — Jira is a REST API, not a git host.

All credential bind-mounts SHALL be read-only so a compromised container cannot rewrite host config or tokens. `~/.aws/credentials` and `~/.aws/cli/cache/` SHALL NEVER be mounted, even under `--aws`.

#### Scenario: --jira forwards host env vars

- **GIVEN** `JIRA_USER_EMAIL=user@example.com`, `JIRA_BASE_URL=https://example.atlassian.net`, and `JIRA_API_TOKEN=faketoken` are exported in the host shell
- **WHEN** user runs `claude-docker --jira ~/repo`
- **THEN** `echo $JIRA_USER_EMAIL` inside the container prints `user@example.com`
- **AND** `echo $JIRA_BASE_URL` inside the container prints `https://example.atlassian.net`
- **AND** `echo $JIRA_API_TOKEN` inside the container prints `faketoken`
- **AND** `git config --system --list | grep -c insteadOf` inside the container is `0` (no rewrite injected by this flag)

#### Scenario: --jira pulls JIRA_API_TOKEN from 1Password when unset on host

- **GIVEN** `JIRA_API_TOKEN` is **not** set in the host shell
- **AND** `CLAUDE_DOCKER_JIRA_OP_REF=op://SomeVault/jira/api-token` is exported
- **AND** the host has `op` on PATH signed in to a service account that can read that reference
- **WHEN** user runs `claude-docker --jira ~/repo`
- **THEN** `echo $JIRA_API_TOKEN` inside the container prints the resolved value from 1Password (non-empty)

#### Scenario: --jira is silent when neither host env nor op-read produces a token

- **GIVEN** `JIRA_API_TOKEN` is not set on the host
- **AND** `CLAUDE_DOCKER_JIRA_OP_REF` is not set on the host (or is set but `op` is missing / signed out)
- **WHEN** user runs `claude-docker --jira ~/repo`
- **THEN** the container starts without error
- **AND** `echo $JIRA_API_TOKEN` inside the container is empty
- **AND** any in-container Jira call fails loudly with the script's own missing-env handling (e.g. `error: JIRA_API_TOKEN not set`)

#### Scenario: no --jira means no Jira credentials reach the container

- **GIVEN** `JIRA_USER_EMAIL`, `JIRA_BASE_URL`, and `JIRA_API_TOKEN` are all exported in the host shell
- **WHEN** user runs `claude-docker ~/repo` without `--jira`
- **THEN** `echo $JIRA_USER_EMAIL` inside the container is empty
- **AND** `echo $JIRA_BASE_URL` inside the container is empty
- **AND** `echo $JIRA_API_TOKEN` inside the container is empty
