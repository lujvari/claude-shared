## ADDED Requirements

### Requirement: npm feed credential opt-in

`run.sh` SHALL forward `NPM_FEED_PASSWORD` into the container only when the user passes `--npm-feed`, and only when non-empty. It SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_NPM_FEED_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. There SHALL be no built-in default reference and no bind mount. When the flag is set, `run.sh` SHALL add `npm-feed` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `NPM_FEED_PASSWORD` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Feed credential reaches a CT box

- **GIVEN** `CLAUDE_DOCKER_NPM_FEED_OP_REF` names a readable item
- **AND** `~/.npmrc` sets the feed's `_password` to `${NPM_FEED_PASSWORD}`
- **WHEN** the user runs `cd-ct`
- **THEN** `npm view` of a package on the feed succeeds inside the box
- **AND** `CLAUDE_DOCKER_FLAGS` contains `npm-feed`

#### Scenario: No flag, no feed credential

- **GIVEN** `NPM_FEED_PASSWORD` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--npm-feed`
- **THEN** `NPM_FEED_PASSWORD` is not set inside the container
- **AND** `npm view left-pad version` still succeeds

#### Scenario: Unresolved credential aborts

- **GIVEN** `NPM_FEED_PASSWORD` and `CLAUDE_DOCKER_NPM_FEED_OP_REF` are unset on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --npm-feed ~/repo`
- **THEN** `run.sh` names `--npm-feed` on stderr and exits non-zero without starting a container
