## ADDED Requirements

### Requirement: AWS state never persists in the shared home

In a non-ephemeral box, `run.sh` SHALL mount an empty tmpfs owned by the box
user at `/home/claude/.aws`, with or without `--aws`. Under `--aws`, the
read-only `config` and `sso` mounts SHALL sit on top of that tmpfs, and the
static-key profile written by the entrypoint SHALL land on the tmpfs. No AWS
file written in one box SHALL be visible in another box.

#### Scenario: Static keys do not outlive the box

- **GIVEN** a box was launched with `--aws` and static keys, so `~/.aws/credentials` holds the `aegon` profile
- **WHEN** the user launches a second box without `--aws`
- **THEN** `~/.aws/` in the second box is empty

#### Scenario: Stale volume state is hidden

- **GIVEN** the `claude-code-root` volume holds `.aws/credentials` from before this change
- **WHEN** the user launches any non-ephemeral box
- **THEN** that file is not visible inside the box
