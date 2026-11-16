## ADDED Requirements

### Requirement: Mount inat user rules read-only

`run.sh` SHALL resolve the host config directory to its real path, take its parent as the rules home, and, when `<rules home>/.inat/rules` is a directory, bind-mount it read-only at `/home/claude/.inat/rules` in the container. It SHALL mount no other part of `<rules home>/.inat`. When the directory is absent, `run.sh` SHALL mount nothing there. It SHALL print one warning naming the path it checked only when the host `CLAUDE.md` contains the text `~/.inat/rules/`; otherwise it SHALL print nothing. The mount SHALL apply under `--ro` and `--ephemeral` as well. The image SHALL provide `/home/claude/.inat` owned by the box user, so the mount never leaves it root-owned.

#### Scenario: Rules are visible at the path CLAUDE.md points to

- **GIVEN** the host config dir is `<home>/.claude` and `<home>/.inat/rules/inat-usage.md` exists
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** `/home/claude/.inat/rules/inat-usage.md` inside the container has the same contents as the host file

#### Scenario: Rules follow --claude-dir

- **GIVEN** `/tmp/h/.claude/CLAUDE.md` and `/tmp/h/.inat/rules/x.md` exist on the host
- **WHEN** the user runs `claude-docker --claude-dir=/tmp/h/.claude ~/repo`
- **THEN** `/home/claude/.inat/rules/x.md` exists inside the container

#### Scenario: Rules are read-only from inside

- **GIVEN** a container launched with the rules mounted
- **WHEN** a process inside writes a file under `/home/claude/.inat/rules`
- **THEN** the write fails with a read-only filesystem error

#### Scenario: Only the rules directory is mounted

- **GIVEN** the host has `<home>/.inat/config.json` and `<home>/.inat/rules/`
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** the only mount under `/home/claude/.inat` listed in `/proc/mounts` is `/home/claude/.inat/rules`

#### Scenario: No rules and no pointers launches silently

- **GIVEN** the host has no `<home>/.inat/rules` and its `CLAUDE.md` has no `~/.inat/rules/` text
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** the container starts, `run.sh` prints nothing about inat, and `/proc/mounts` lists nothing at `/home/claude/.inat/rules`

#### Scenario: Pointers without rules warn

- **GIVEN** the host `CLAUDE.md` contains `~/.inat/rules/inat-usage.md` and `<home>/.inat/rules` does not exist
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** `run.sh` prints one warning naming `<home>/.inat/rules`
- **AND** the container starts

#### Scenario: In-box inat can still write its cache

- **GIVEN** a container started with `--ephemeral` and the rules mounted
- **WHEN** a process inside creates `/home/claude/.inat/cache/probe`
- **THEN** the write succeeds
