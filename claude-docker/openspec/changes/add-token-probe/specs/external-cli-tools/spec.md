## ADDED Requirements

### Requirement: Launch-time token probe

After the fail-closed credential gate passes and before `docker run`, `run.sh` SHALL make one authenticated identity request per credential flag set on the launch, for the flags and endpoints listed in the `add-token-probe` design. When a service answers that the token is rejected, `run.sh` SHALL print one stderr line naming the flag and the HTTP status, and SHALL continue the launch. On a network error, a timeout, a 5xx or any other status, `run.sh` SHALL print nothing for that flag. Probes SHALL run in parallel with a 1 s connect timeout and a 2 s total timeout. No token value SHALL appear in a process's argv or in `run.sh` output. `run.sh` SHALL pass the rejected flags into the container as `CLAUDE_DOCKER_REJECTED_TOKENS`, comma-separated without leading dashes, and the statusline wrapper SHALL show them as a `token-dead:<flags>` tag. When `CLAUDE_DOCKER_NO_TOKEN_PROBE=1` is set, or `curl` is not on PATH, `run.sh` SHALL skip every probe.

#### Scenario: Revoked token warns and launches

- **GIVEN** `GITLAB_TOKEN` is set but revoked, and `api/v4/user` answers 401
- **WHEN** the user runs `claude-docker --glab ~/repo`
- **THEN** stderr carries `claude-docker: --glab token rejected (HTTP 401) - rotate it on the host before relying on this box`
- **AND** the container starts with `CLAUDE_DOCKER_REJECTED_TOKENS=glab`
- **AND** the statusline shows `token-dead:glab`

#### Scenario: Offline launch stays quiet

- **GIVEN** the host has no network route
- **WHEN** the user runs `claude-docker --gh ~/repo`
- **THEN** no probe line is printed
- **AND** the container starts within 2 s of when it would have without the probe

#### Scenario: Token never reaches argv

- **GIVEN** `--gh` with `GH_TOKEN` set
- **WHEN** the probe runs
- **THEN** the `curl` process's argv does not contain the token

#### Scenario: Opt-out

- **GIVEN** `CLAUDE_DOCKER_NO_TOKEN_PROBE=1`
- **WHEN** the user runs `claude-docker --gh --jira ~/repo`
- **THEN** no identity request is made

#### Scenario: Valid token is quiet

- **GIVEN** `--sonar` with a valid `SONAR_TOKEN`, and `api/authentication/validate` answers `{"valid":true}`
- **WHEN** the probe runs
- **THEN** nothing is printed for `--sonar`
