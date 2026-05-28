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

All credential bind-mounts SHALL be read-only so a compromised container cannot rewrite host config or tokens. `~/.aws/credentials` and `~/.aws/cli/cache/` SHALL NEVER be mounted, even under `--aws`.

#### Scenario: --ado forwards host PAT env var

- **GIVEN** `AZURE_DEVOPS_EXT_PAT=fakepat` is exported in the host shell
- **WHEN** user runs `claude-docker --ado ~/repo`
- **THEN** `echo $AZURE_DEVOPS_EXT_PAT` inside the container prints `fakepat`
- **AND** `git config --system --get-all url.https://oauth2:fakepat@dev.azure.com.insteadOf` inside the container prints `https://dev.azure.com`

#### Scenario: --ado is silent without a host PAT

- **GIVEN** `AZURE_DEVOPS_EXT_PAT` is not set in the host shell
- **WHEN** user runs `claude-docker --ado ~/repo`
- **THEN** the container starts without error
- **AND** `echo $AZURE_DEVOPS_EXT_PAT` inside the container is empty
- **AND** `git config --system --get-all url.https://dev.azure.com.insteadOf` inside the container exits non-zero (no rewrite injected)

#### Scenario: --ado honors CLAUDE_DOCKER_ADO_HOSTS override

- **GIVEN** `AZURE_DEVOPS_EXT_PAT=fakepat` and `CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com,myorg.visualstudio.com` are exported in the host shell
- **WHEN** user runs `claude-docker --ado ~/repo`
- **THEN** `git config --system --list` inside the container contains insteadOf entries for both `dev.azure.com` and `myorg.visualstudio.com`

#### Scenario: no --ado means no Azure DevOps credentials reach the container

- **GIVEN** `AZURE_DEVOPS_EXT_PAT=fakepat` is exported in the host shell
- **WHEN** user runs `claude-docker ~/repo` without `--ado`
- **THEN** `echo $AZURE_DEVOPS_EXT_PAT` inside the container is empty
- **AND** `git config --system --list | grep dev.azure.com` inside the container produces no output
