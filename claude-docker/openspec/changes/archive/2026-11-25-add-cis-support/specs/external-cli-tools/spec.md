## ADDED Requirements

### Requirement: CIS credential opt-in

`run.sh` SHALL forward `CIS_API_KEY` into the container only when the user passes `--cis`, and only when non-empty. It SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_CIS_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. There SHALL be no built-in default reference and no bind mount. When the flag is set, `run.sh` SHALL add `cis` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `CIS_API_KEY` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Key is read from 1Password when unset on the host

- **GIVEN** `CIS_API_KEY` is not set on the host
- **AND** `CLAUDE_DOCKER_CIS_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --cis ~/repo`
- **THEN** `CIS_API_KEY` inside the container is non-empty
- **AND** `CLAUDE_DOCKER_FLAGS` contains `cis`

#### Scenario: No flag, no key

- **GIVEN** `CIS_API_KEY` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--cis`
- **THEN** `CIS_API_KEY` is not set inside the container

#### Scenario: Unresolved key aborts

- **GIVEN** `CIS_API_KEY` and `CLAUDE_DOCKER_CIS_OP_REF` are unset on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --cis ~/repo`
- **THEN** `run.sh` names `--cis` on stderr and exits non-zero without starting a container
