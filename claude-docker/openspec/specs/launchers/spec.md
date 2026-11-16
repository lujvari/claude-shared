# launchers Specification

## Purpose
Behaviour of the per-project `cd-*` launchers in `launchers/` beyond the `run.sh` flags they pass, starting with the lifecycle of a project's test database.
## Requirements
### Requirement: Test database stops when the last box of its project exits

A launcher that brings up a test database (`cd-brain`: `brain-test-postgres`; `cd-mep`: `myentrypoint-test-postgres`) SHALL take a shared lock on `~/.cache/claude-docker/locks/<container>.lock` before bringing the database up, and SHALL hold it until its box exits. On exit, normal or by INT, TERM or HUP, the launcher SHALL stop every container of the database's compose project if, and only if, no other launcher holds that lock. It SHALL NOT remove containers, networks or volumes. It SHALL exit with the box's exit status whether or not the stop succeeds. A launch that starts while a stop is in progress SHALL wait for the stop to finish before bringing the database up.

#### Scenario: Last box out stops the database

- **GIVEN** one `cd-brain` box is running and `brain-test-postgres` is up
- **WHEN** the user exits `claude` in that box
- **THEN** `brain-test-postgres` is stopped, not removed
- **AND** the `brain-test_pgdata` volume still exists
- **AND** the launcher exits with `claude`'s exit status
- **AND** stderr shows `brain-test-postgres stopped (last box out)`

#### Scenario: Another box of the same project keeps it running

- **GIVEN** two `cd-mep` boxes are running
- **WHEN** the first one exits
- **THEN** `myentrypoint-test-postgres` is still running and reachable from the second box
- **AND** stderr shows `myentrypoint-test-postgres left running: another box holds it`
- **WHEN** the second one exits
- **THEN** `myentrypoint-test-postgres` is stopped

#### Scenario: A box still launching counts as running

- **GIVEN** box A of `cd-brain` is running
- **AND** box B of `cd-brain` has passed its `up --wait` but has not reached `docker run`
- **WHEN** box A exits
- **THEN** `brain-test-postgres` is left running

#### Scenario: Terminal closed

- **GIVEN** one `cd-brain` box is running in a terminal
- **WHEN** the terminal is closed (the launcher receives HUP)
- **THEN** `brain-test-postgres` is stopped

#### Scenario: Next launch restarts a stopped database

- **GIVEN** `brain-test-postgres` was stopped by a previous last-box exit
- **WHEN** the user runs `cd-brain`
- **THEN** the database is up, healthy and published on 47401 before the box starts, with its previous data

### Requirement: cd-up relaunches the box fleet in Windows Terminal tabs

`launchers/cd-up` SHALL hold a hard-coded list of box names (the `cd-<name>` launchers the owner keeps open). Run with no arguments it SHALL relaunch every listed box; run with names it SHALL relaunch only those, and SHALL reject an unknown name before opening any tab. Before opening any tab it SHALL wait, up to a bounded timeout, for `docker info` to succeed, and SHALL then check `op whoami` once; if either fails it SHALL print one line naming the cause and exit non-zero without opening a tab. For each box it SHALL make one separate `wt.exe -w 0 new-tab --title cd-<name>` call that runs `cd-<name> -- --continue` under `bash -lic` and leaves an interactive shell in the tab after the box exits or fails. Consecutive tab launches SHALL be spaced by a fixed delay. The command passed to `wt.exe` SHALL contain no `;` character. Given `--yolo` before the box names, it SHALL pass `--yolo` to every box it opens; without it, it SHALL NOT. An unknown option SHALL exit 2 before any check or tab.

#### Scenario: Named boxes come up resumed

- **GIVEN** Docker is running and `op whoami` succeeds
- **WHEN** the owner runs `cd-up mep cis` from a WSL shell inside Windows Terminal
- **THEN** two new tabs titled `cd-mep` and `cd-cis` open in the current window, about 3 s apart
- **AND** each tab shows its box resuming the previous conversation

#### Scenario: 1Password not authenticated

- **GIVEN** Docker is running and `op whoami` fails
- **WHEN** the owner runs `cd-up`
- **THEN** one line says 1Password is not authenticated
- **AND** no tab opens and the exit status is non-zero

#### Scenario: Docker never comes up

- **GIVEN** `docker info` keeps failing
- **WHEN** the timeout passes
- **THEN** one line says Docker did not come up and no tab opens

#### Scenario: Unknown box name

- **WHEN** the owner runs `cd-up mep nope`
- **THEN** it names `nope` as unknown, lists the valid names, and opens no tab

#### Scenario: A failed launch stays open

- **GIVEN** a box's launch aborts (for example an `op read` timeout)
- **WHEN** its launcher exits
- **THEN** the tab stays open at a shell with the error visible

#### Scenario: --yolo is opt-in

- **WHEN** the owner runs `cd-up --yolo mep cis`
- **THEN** both tabs run `cd-mep --yolo -- --continue` and `cd-cis --yolo -- --continue`
- **WHEN** the owner runs `cd-up mep`
- **THEN** the tab runs `cd-mep -- --continue`, without `--yolo`

#### Scenario: Unknown option

- **WHEN** the owner runs `cd-up --yolp mep`
- **THEN** it names `--yolp` as unknown, exits 2, and neither checks Docker nor opens a tab

