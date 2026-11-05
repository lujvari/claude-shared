## ADDED Requirements

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
