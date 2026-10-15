## ADDED Requirements

### Requirement: Credential flags fail closed

When the user passes a credential flag, `run.sh` SHALL NOT start a container that lacks the credential that flag asked for. It SHALL abort before `docker run` with a non-zero exit and a stderr message naming the flag or the op-ref when: `op` is not on PATH while a flag needs it; the `op whoami` preflight fails; any `op read` fails; or, after all credential sources, none of the flag's env vars is set. The end-state check SHALL cover `--gh`, `--glab`, `--ado`, `--ado-admin`, `--jira`, `--supabase`, `--cloudflare`, `--openrouter`, `--sonar`, `--mepdb`, `--rr-e2e` and `--hetzner-infra`, and SHALL NOT cover `--aws`, `--tfe` or `--tofu`, whose credentials may arrive by mount. When `CLAUDE_DOCKER_OP_OPTIONAL=1` is set, each of these aborts SHALL instead print a warning and the launch SHALL continue. This requirement takes precedence over any earlier clause saying `run.sh` continues silently when a token cannot be resolved.

#### Scenario: Failed read aborts the launch

- **GIVEN** `POSTGRES_TEST_URL` is unset on the host and `op read` of the `--mepdb` ref fails
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** stderr names the ref that was not delivered
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: --gh with no token source aborts

- **GIVEN** neither `GH_TOKEN` nor `GITHUB_TOKEN` is set, `CLAUDE_DOCKER_GITHUB_OP_REF` is unset, and `gh auth token` yields nothing
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --gh ~/repo`
- **THEN** stderr says `--gh` injected nothing
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: Expired token is reported once

- **GIVEN** no host `GH_TOKEN`/`GITHUB_TOKEN`/`POSTGRES_TEST_URL`, and `CLAUDE_DOCKER_GITHUB_OP_REF` is set
- **AND** `op whoami` returns (403) Forbidden
- **WHEN** the user runs `claude-docker --gh --mepdb ~/repo`
- **THEN** stderr carries one preflight failure naming both flags, and no per-ref read errors
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: Escape hatch launches without the credential

- **GIVEN** the `--mepdb` read fails
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL=1` is set
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** stderr warns that the container will be missing the credential
- **AND** the container starts without `POSTGRES_TEST_URL`

#### Scenario: Mount-based flags are not asserted

- **GIVEN** the host has `~/.aws/config` and an SSO cache but no `AWS_ACCESS_KEY_ID` and no `CLAUDE_DOCKER_AWS_OP_REF`
- **WHEN** the user runs `claude-docker --aws ~/repo`
- **THEN** the container starts
