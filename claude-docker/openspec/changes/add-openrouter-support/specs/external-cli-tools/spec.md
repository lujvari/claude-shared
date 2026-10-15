## ADDED Requirements

### Requirement: OpenRouter credential opt-in

`run.sh` SHALL forward `OPENROUTER_API_KEY` into the container only when the user passes `--openrouter`. The value SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_OPENROUTER_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. There SHALL be no built-in default reference, no bind mount, no CLI-login fallback, and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `openrouter` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `OPENROUTER_API_KEY` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Host env var is forwarded

- **GIVEN** `OPENROUTER_API_KEY=fakekey` is exported on the host
- **WHEN** the user runs `claude-docker --openrouter ~/repo`
- **THEN** `echo $OPENROUTER_API_KEY` inside the container prints `fakekey`
- **AND** `CLAUDE_DOCKER_FLAGS` contains `openrouter`

#### Scenario: Key is read from 1Password when unset on the host

- **GIVEN** `OPENROUTER_API_KEY` is not set on the host
- **AND** `CLAUDE_DOCKER_OPENROUTER_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --openrouter ~/repo`
- **THEN** `OPENROUTER_API_KEY` inside the container is non-empty

#### Scenario: No flag, no key

- **GIVEN** `OPENROUTER_API_KEY` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--openrouter`
- **THEN** `OPENROUTER_API_KEY` is not set inside the container

#### Scenario: Flag that resolves to nothing aborts the launch

- **GIVEN** neither `OPENROUTER_API_KEY` nor `CLAUDE_DOCKER_OPENROUTER_OP_REF` is set on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --openrouter ~/repo`
- **THEN** `run.sh` names `--openrouter` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--openrouter` and `CLAUDE_DOCKER_OPENROUTER_OP_REF`
