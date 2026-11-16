## MODIFIED Requirements

### Requirement: cd-up relaunches the box fleet in Windows Terminal tabs

`launchers/cd-up` SHALL hold a hard-coded list of box names (the `cd-<name>` launchers the owner keeps open), split into groups, one group per Windows Terminal window. Run with no arguments it SHALL relaunch every listed box; run with names it SHALL relaunch only those, and SHALL reject an unknown name before opening any tab. Before opening any tab it SHALL wait, up to a bounded timeout, for `docker info` to succeed. It SHALL then skip every requested box whose container is already running, printing one line per skipped box, and SHALL say so and exit 0 without a further check when none is left. A box named more than once SHALL be handled once. If the running check itself fails it SHALL print one line and exit non-zero without opening a tab. Otherwise it SHALL check `op whoami` once; if either check fails it SHALL print one line naming the cause and exit non-zero without opening a tab. For each box it SHALL make one separate `wt.exe` call that opens a tab titled `cd-<name>` in the named window of the box's group, at that group's fixed position and size when the window does not exist yet, and runs `cd-<name> -- --continue` under `bash -lic`, leaving an interactive shell in the tab after the box exits or fails. Consecutive tab launches SHALL be spaced by a fixed delay. The command passed to `wt.exe` SHALL contain no `;` character. Given `--yolo` before the box names, it SHALL pass `--yolo` to every box it opens; without it, it SHALL NOT. An unknown option SHALL exit 2 before any check or tab.

#### Scenario: Named boxes come up resumed

- **GIVEN** Docker is running, `op whoami` succeeds and neither box is running
- **WHEN** the owner runs `cd-up mep cis` from a WSL shell inside Windows Terminal
- **THEN** a tab titled `cd-mep` opens in window `cd-q3` and one titled `cd-cis` in window `cd-q4`, about 3 s apart
- **AND** each tab shows its box resuming the previous conversation

#### Scenario: The fleet lands in its quarters

- **GIVEN** no Windows Terminal window named `cd-q1`, `cd-q3` or `cd-q4` exists and no box is running
- **WHEN** the owner runs `cd-up`
- **THEN** three windows open, each at its group's position and size, holding `apg asr`, `tools dev mep` and `brain cis ct inat` as tabs

#### Scenario: An existing group window is reused

- **GIVEN** window `cd-q4` is open
- **WHEN** the owner runs `cd-up cis`
- **THEN** the `cd-cis` tab joins window `cd-q4` and no new window opens

#### Scenario: A running box is skipped

- **GIVEN** the `cd-cis` box is running
- **WHEN** the owner runs `cd-up` or `cd-up cis mep`
- **THEN** one line says `cd-up: skipped cd-cis (already running)` and no tab opens for it
- **AND** every other requested box opens as usual

#### Scenario: Running check fails

- **GIVEN** `docker info` succeeds but listing containers fails
- **WHEN** the owner runs `cd-up`
- **THEN** one line says the running check failed, no tab opens and the exit status is non-zero

#### Scenario: A box named twice

- **WHEN** the owner runs `cd-up mep mep`
- **THEN** one `cd-mep` tab opens

#### Scenario: Everything already running

- **GIVEN** every requested box is running
- **WHEN** the owner runs `cd-up`
- **THEN** each box gets its skipped line, one line says there is nothing to open, `op whoami` is not run, no tab opens and the exit status is 0

#### Scenario: 1Password not authenticated

- **GIVEN** Docker is running, at least one requested box is not running, and `op whoami` fails
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

## ADDED Requirements

### Requirement: A launched box's container names its launcher

A container started through a `cd-<name>` launcher SHALL carry a Docker label `claude-docker.box=cd-<name>`, so a running box can be found by its launcher's name. A container started from `run.sh` directly SHALL carry the label with an empty value.

#### Scenario: Running box found by name

- **GIVEN** the owner started `cd-cis`
- **WHEN** `docker ps --filter label=claude-docker.box=cd-cis` runs on the host
- **THEN** it lists that box's container, and only that one
