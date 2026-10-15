## ADDED Requirements

### Requirement: Launcher directory read-only under broad mounts

When a workspace argument strictly contains the directory holding `run.sh` (the launcher directory), `run.sh` SHALL bind-mount the launcher directory read-only over its path inside that workspace's container mount. Only the launcher directory SHALL be overlaid; the rest of the workspace, including other directories next to it, SHALL keep the workspace's mode. The overlay SHALL NOT be added when `--ro` is set, when `--tools` is set, or when the workspace argument is the launcher directory itself.

#### Scenario: Broad mount pins the launcher

- **GIVEN** the launcher directory is `<dev-root>/tools/claude-shared/claude-docker`
- **WHEN** the user runs `claude-docker --yolo <dev-root>`
- **THEN** writing a file under `/workspaces/<dev-root-name>/tools/claude-shared/claude-docker` inside the container fails with a read-only filesystem error
- **AND** writing a file elsewhere under `/workspaces/<dev-root-name>/tools` succeeds

#### Scenario: --tools keeps the launcher writable

- **WHEN** the user runs `claude-docker --tools <dev-root>`
- **THEN** no read-only overlay is added for the launcher directory
- **AND** writing under the launcher directory inside the container succeeds

#### Scenario: Mounting the launcher directly stays writable

- **WHEN** the user runs `claude-docker <dev-root>/tools/claude-shared/claude-docker`
- **THEN** the workspace is writable without `--tools`

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--tools`
