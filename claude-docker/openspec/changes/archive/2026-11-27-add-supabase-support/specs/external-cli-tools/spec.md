## ADDED Requirements

### Requirement: Supabase credential opt-in

`run.sh` SHALL forward `SUPABASE_ACCESS_TOKEN` into the container only when the user passes `--supabase`. The value SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_SUPABASE_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host and forward the result. There SHALL be no built-in default reference, no bind mount, and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `supabase` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and, after both sources, `SUPABASE_ACCESS_TOKEN` is empty or the `op read` failed, `run.sh` SHALL abort before `docker run` with a non-zero exit unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Host env var is forwarded

- **GIVEN** `SUPABASE_ACCESS_TOKEN=faketoken` is exported on the host
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `echo $SUPABASE_ACCESS_TOKEN` inside the container prints `faketoken`
- **AND** `CLAUDE_DOCKER_FLAGS` contains `supabase`

#### Scenario: Token is read from 1Password when unset on the host

- **GIVEN** `SUPABASE_ACCESS_TOKEN` is not set on the host
- **AND** `CLAUDE_DOCKER_SUPABASE_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `SUPABASE_ACCESS_TOKEN` inside the container is non-empty

#### Scenario: No flag, no token

- **GIVEN** `SUPABASE_ACCESS_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--supabase`
- **THEN** `SUPABASE_ACCESS_TOKEN` is not set inside the container

#### Scenario: Flag that resolves to nothing aborts the launch

- **GIVEN** `SUPABASE_ACCESS_TOKEN` and `CLAUDE_DOCKER_SUPABASE_OP_REF` are both unset on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `run.sh` names `--supabase` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--supabase` and `CLAUDE_DOCKER_SUPABASE_OP_REF`
