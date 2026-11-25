## ADDED Requirements

### Requirement: npm feed credential derived from the ADO PAT

When the user passes `--npm-feed`, `run.sh` SHALL set `NPM_FEED_PASSWORD` in the container to the base64 encoding, without line breaks, of the `AZURE_DEVOPS_EXT_PAT` the box receives. `--npm-feed` without `--ado` SHALL abort before `docker run` with an error naming both flags. Without `--npm-feed`, `NPM_FEED_PASSWORD` SHALL NOT be set in the container, even when the host has it. When the flag is set, `run.sh` SHALL add `npm-feed` to `CLAUDE_DOCKER_FLAGS`.

#### Scenario: Feed credential reaches a CT box

- **GIVEN** `~/.npmrc` sets the feed's `_password` to `${NPM_FEED_PASSWORD}`
- **AND** the `--ado` PAT has Packaging (Read) on the feed
- **WHEN** the user runs `cd-ct`
- **THEN** `npm view` of a package on the feed succeeds inside the box
- **AND** `CLAUDE_DOCKER_FLAGS` contains `npm-feed`

#### Scenario: No flag, no feed credential

- **WHEN** the user runs `claude-docker --ado ~/repo` without `--npm-feed`
- **THEN** `NPM_FEED_PASSWORD` is not set inside the container
- **AND** `npm view left-pad version` still succeeds

#### Scenario: Flag without --ado aborts

- **WHEN** the user runs `claude-docker --npm-feed ~/repo`
- **THEN** `run.sh` names `--npm-feed` and `--ado` on stderr and exits non-zero without starting a container
