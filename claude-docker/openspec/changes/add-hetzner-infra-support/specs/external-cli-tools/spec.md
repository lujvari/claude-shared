## ADDED Requirements

### Requirement: Hetzner Cloud infrastructure opt-in

`run.sh` SHALL forward `HCLOUD_TOKEN` into the container only when the user passes `--hetzner-infra`. The value SHALL come from the host environment when set there; otherwise `run.sh` SHALL resolve `CLAUDE_DOCKER_HETZNER_OP_REF` with `op read` on the host. That variable SHALL default to `op://claude-docker-infra/hcloud-mep/token` when unset, and an explicitly empty value SHALL disable the 1Password path.

The read SHALL use the 1Password service-account token stored in the file named by `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` (default `~/.config/op/infra-service-account-token`), set only for that one read. It SHALL NOT be forwarded into the container or used for any other flag's read. When `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` is explicitly empty, the read SHALL use the everyday service account instead.

When the token file is missing, is empty, or does not start with `ops_`, `run.sh` SHALL report the file path (never its content) and treat the reference as a failed read. While a token file is in use, a failed everyday `op whoami` preflight SHALL NOT block a launch whose only 1Password read is this one.

There SHALL be no bind mount and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `hetzner-infra` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `HCLOUD_TOKEN` is still empty, or the read failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Token is read with the infra service account

- **GIVEN** `HCLOUD_TOKEN` is not set on the host
- **AND** the default token file holds a service-account token that can read the default reference
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo`
- **THEN** `HCLOUD_TOKEN` inside the container is non-empty
- **AND** `OP_SERVICE_ACCOUNT_TOKEN` is not set inside the container
- **AND** `CLAUDE_DOCKER_FLAGS` contains `hetzner-infra`

#### Scenario: Other flags keep the everyday account

- **GIVEN** the infra token file is valid
- **WHEN** the user runs `claude-docker --mepdb --hetzner-infra ~/repo`
- **THEN** the `--mepdb` reference is read with the everyday service account
- **AND** only the `--hetzner-infra` reference is read with the infra service account

#### Scenario: Missing or malformed token file aborts the launch

- **GIVEN** `HCLOUD_TOKEN` is not set on the host
- **AND** the token file is missing, empty, or does not start with `ops_`
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo`
- **THEN** `run.sh` names the token file path and the reference on stderr without printing the file's content
- **AND** exits non-zero without starting a container

#### Scenario: Dead everyday account does not block an infra-only launch

- **GIVEN** the everyday service-account token is revoked
- **AND** the infra token file is valid
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo` with no other 1Password-backed flag
- **THEN** the container starts with `HCLOUD_TOKEN` set

#### Scenario: No flag, no token

- **GIVEN** `HCLOUD_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--hetzner-infra`
- **THEN** `HCLOUD_TOKEN` is not set inside the container

#### Scenario: Help lists the flag and its defaults

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--hetzner-infra`, `op://claude-docker-infra/hcloud-mep/token` and `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE`
