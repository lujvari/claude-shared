## ADDED Requirements

### Requirement: Unprivileged box user

The container SHALL run as uid 1000 / gid 1000 (user `claude`, `HOME=/home/claude`). `run.sh` SHALL pass `--user 1000:1000`, `--cap-drop ALL` and `--security-opt no-new-privileges`, and SHALL add no capability back. The image SHALL contain no sudo and no setuid binary added by this project, and the entrypoint SHALL NOT start as root to drop privileges later.

#### Scenario: Box writes are owned by the WSL user

- **GIVEN** a workspace under `/mnt/c/dev` mounted into a box
- **WHEN** the box creates a file in it
- **THEN** WSL shows the file owned by uid 1000

#### Scenario: No privilege to regain root

- **WHEN** a process in the box runs `id -u`
- **THEN** it prints `1000`
- **AND** its effective capability set is empty

### Requirement: Home layout survives the user change

The `claude-code-root` volume SHALL mount at `/home/claude` and `claude-code-home` at `/home/claude/.claude`. `/root` SHALL be a symlink to `/home/claude` so absolute `/root/...` paths recorded by earlier images still resolve. The entrypoint SHALL exit non-zero, naming the README migration, when `~/.local/bin` or `~/.claude` (or `~/.aws` when static AWS keys are forwarded) is not writable.

#### Scenario: Unmigrated volume

- **GIVEN** a `claude-code-root` volume still owned by uid 0
- **WHEN** a box starts
- **THEN** the entrypoint exits with a message pointing at the one-off migration
