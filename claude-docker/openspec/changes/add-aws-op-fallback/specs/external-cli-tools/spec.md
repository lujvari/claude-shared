## MODIFIED Requirements

### Requirement: Credentials opt-in

Host credentials (files or env vars) SHALL NOT reach the container unless the user explicitly opts in per-run. `run.sh` defaults to no credential mounts and no token env forwarding. Opt-ins are granted via dedicated flags:

- `--aws`: mount `~/.aws/config` at `/root/.aws/config:ro` and, when present, `~/.aws/sso/` at `/root/.aws/sso:ro`; forward `AWS_PROFILE`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` when set on the host. When `AWS_ACCESS_KEY_ID` is unset on the host and `CLAUDE_DOCKER_AWS_OP_REF` is set to an `op://` 1Password item reference (e.g. `op://claude-docker/aegon-aws`), `run.sh` SHALL run `op read` on the host for each canonical sub-field of that item and forward the resolved values as the matching `AWS_*` env vars: `access_key_id` → `AWS_ACCESS_KEY_ID` (required), `secret_access_key` → `AWS_SECRET_ACCESS_KEY` (required), `session_token` → `AWS_SESSION_TOKEN` (optional), `region` → `AWS_REGION` (optional, host `AWS_REGION` wins when both are set). Trailing `/` on the ref SHALL be tolerated. Required fields missing → silent no-op; on `op` missing / sign-out / item-absent, `run.sh` SHALL continue silently. The 1P fallback covers static IAM-user keys (or pre-exported STS bundles); SSO sessions continue to use the host-side `aws sso login` cache mount.
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

#### Scenario: --aws resolves static keys from 1Password when host AWS env is empty

- **GIVEN** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` are all unset in the host shell
- **AND** `CLAUDE_DOCKER_AWS_OP_REF=op://claude-docker/aegon-aws` is exported
- **AND** the host has `op` on PATH signed in to a service account that can read that reference
- **AND** the 1P item has fields `access_key_id` and `secret_access_key` with non-empty values
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `echo $AWS_ACCESS_KEY_ID` inside the container is the resolved 1P access-key-id (non-empty)
- **AND** `echo $AWS_SECRET_ACCESS_KEY` inside the container is the resolved 1P secret-access-key (non-empty)

#### Scenario: --aws OP fallback forwards optional session_token and region when present

- **GIVEN** the gate conditions of the previous scenario are met
- **AND** the 1P item also has fields `session_token` and `region` with non-empty values
- **AND** `AWS_REGION` is not set in the host shell
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `echo $AWS_SESSION_TOKEN` inside the container is the resolved 1P session-token (non-empty)
- **AND** `echo $AWS_REGION` inside the container is the resolved 1P region (non-empty)

#### Scenario: --aws OP fallback respects host AWS_REGION precedence

- **GIVEN** `AWS_ACCESS_KEY_ID` is unset and `CLAUDE_DOCKER_AWS_OP_REF` is set as above
- **AND** the 1P item's `region` field is `eu-north-1`
- **AND** `AWS_REGION=eu-west-1` is exported in the host shell
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `echo $AWS_REGION` inside the container is `eu-west-1` (host value wins)

#### Scenario: --aws OP fallback is silent when required fields are absent

- **GIVEN** `AWS_ACCESS_KEY_ID` is unset on the host
- **AND** `CLAUDE_DOCKER_AWS_OP_REF` is set
- **AND** the 1P item has `access_key_id` but no `secret_access_key` (or the item does not exist)
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** the container starts without error
- **AND** `echo $AWS_ACCESS_KEY_ID` inside the container is empty
- **AND** `echo $AWS_SECRET_ACCESS_KEY` inside the container is empty

#### Scenario: host AWS env takes precedence over --aws OP fallback

- **GIVEN** `AWS_ACCESS_KEY_ID=AKIAHOST` and `AWS_SECRET_ACCESS_KEY=hostsecret` are exported in the host shell
- **AND** `CLAUDE_DOCKER_AWS_OP_REF=op://claude-docker/aegon-aws` is also exported (with `op` ready)
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `echo $AWS_ACCESS_KEY_ID` inside the container is `AKIAHOST` (not the 1P value)
- **AND** no `op read` calls were issued by `run.sh` for the AWS reference (the gate `[ -z "$AWS_ACCESS_KEY_ID" ]` short-circuits)

#### Scenario: --aws OP fallback ref tolerates a trailing slash

- **GIVEN** `AWS_ACCESS_KEY_ID` is unset on the host
- **AND** `CLAUDE_DOCKER_AWS_OP_REF=op://claude-docker/aegon-aws/` is exported (trailing `/`)
- **AND** the 1P item has `access_key_id` and `secret_access_key`
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `run.sh` resolves the fields as if the ref had no trailing slash
- **AND** `echo $AWS_ACCESS_KEY_ID` inside the container is non-empty

#### Scenario: no --aws means no AWS credentials reach the container even with OP ref set

- **GIVEN** `CLAUDE_DOCKER_AWS_OP_REF` is exported and `op` is ready
- **AND** the 1P item has all four canonical fields
- **WHEN** user runs `claude-docker ~/repo` without `--aws`
- **THEN** `echo $AWS_ACCESS_KEY_ID` inside the container is empty
- **AND** `echo $AWS_SECRET_ACCESS_KEY` inside the container is empty
- **AND** `echo $AWS_REGION` inside the container is empty
