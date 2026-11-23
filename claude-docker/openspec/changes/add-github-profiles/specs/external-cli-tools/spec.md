## ADDED Requirements

### Requirement: Named GitHub profiles

When `--gh` is given and `CLAUDE_DOCKER_GITHUB_PROFILE` names a profile in the launching environment, the box SHALL get its GitHub token only from `CLAUDE_DOCKER_GITHUB_<NAME>_OP_REF`. A `GH_TOKEN` or `GITHUB_TOKEN` from the launching environment or the env file, the default `CLAUDE_DOCKER_GITHUB_OP_REF`, and the host's `gh` login SHALL NOT reach the box. The git credential helper SHALL be set up for `github.com` only, and the persisted in-container `gh` login SHALL be hidden. A missing profile ref or a failed read SHALL abort the launch, even with `CLAUDE_DOCKER_OP_OPTIONAL=1`. `CLAUDE_DOCKER_GITHUB_PROFILE` in the env file SHALL be ignored. Without a profile, `--gh` SHALL behave as before.

#### Scenario: The profile token replaces every default source

- **GIVEN** the env file sets `CLAUDE_DOCKER_GITHUB_OP_REF` to the personal ref and `GH_TOKEN` to a token, and the shell exports `GITHUB_TOKEN`
- **WHEN** a launcher with profile `inat` runs `--gh`
- **THEN** only the inat ref is read from 1Password, and the box's `GH_TOKEN` is that value

#### Scenario: Missing profile ref aborts

- **GIVEN** `CLAUDE_DOCKER_GITHUB_PROFILE=inat` and no `CLAUDE_DOCKER_GITHUB_INAT_OP_REF`
- **WHEN** the launch runs with `--gh`
- **THEN** it exits 1 naming the missing variable, before any 1Password call

#### Scenario: Failed read aborts with no escape hatch

- **GIVEN** a profile whose ref can't be read
- **WHEN** the launch runs with `--gh` and `CLAUDE_DOCKER_OP_OPTIONAL=1`
- **THEN** it exits 1 before `docker run`

#### Scenario: Host gh config can't widen the hosts

- **GIVEN** the host gh config lists a GitHub Enterprise host
- **WHEN** a profile box launches
- **THEN** the box gets `CLAUDE_DOCKER_GITHUB_HOSTS=github.com`

#### Scenario: Stored gh login is hidden

- **GIVEN** a prior `--gh` box ran `gh auth login` (state on `claude-code-root`)
- **WHEN** a profile box launches
- **THEN** `/home/claude/.config/gh` in the box is a fresh tmpfs

#### Scenario: Env file can't make a profile box

- **GIVEN** the env file sets `CLAUDE_DOCKER_GITHUB_PROFILE=inat`
- **WHEN** a launcher without a profile runs `--gh`
- **THEN** the box gets the default GitHub token, as before
