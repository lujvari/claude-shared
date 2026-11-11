## ADDED Requirements

### Requirement: cd-up relaunches the box fleet in Windows Terminal tabs

`launchers/cd-up` SHALL hold a hard-coded list of box names (the `cd-<name>` launchers the owner keeps open). Run with no arguments it SHALL relaunch every listed box; run with names it SHALL relaunch only those, and SHALL reject an unknown name before opening any tab. Before opening any tab it SHALL wait, up to a bounded timeout, for `docker info` to succeed, and SHALL then check `op whoami` once; if either fails it SHALL print one line naming the cause and exit non-zero without opening a tab. For each box it SHALL make one separate `wt.exe -w 0 new-tab --title cd-<name>` call that runs `cd-<name> -- --continue` under `bash -lic` and leaves an interactive shell in the tab after the box exits or fails. Consecutive tab launches SHALL be spaced by a fixed delay. The command passed to `wt.exe` SHALL contain no `;` character.

#### Scenario: Named boxes come up resumed

- **GIVEN** Docker is running and `op whoami` succeeds
- **WHEN** the owner runs `cd-up rr cis` from a WSL shell inside Windows Terminal
- **THEN** two new tabs titled `cd-rr` and `cd-cis` open in the current window, about 3 s apart
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

- **WHEN** the owner runs `cd-up rr nope`
- **THEN** it names `nope` as unknown, lists the valid names, and opens no tab

#### Scenario: A failed launch stays open

- **GIVEN** a box's launch aborts (for example an `op read` timeout)
- **WHEN** its launcher exits
- **THEN** the tab stays open at a shell with the error visible
