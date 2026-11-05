## Why

`cd-brain` and `cd-mep` bring their project's test Postgres up before every
launch (`brain-test-postgres` on 47401, `myentrypoint-test-postgres` on 47304)
and never take it down: both end in `exec "$CD_RUN" ...`, so nothing of the
launcher is left to act when the box exits. The databases run until the next
reboot. `myentrypoint-test-postgres` was seen up for 28h.

## What Changes

- **Stop on last exit.** When a box launched by `cd-brain` or `cd-mep` exits,
  the launcher stops its test database's compose project, unless another box
  of the same project is still running. It stops the containers only. No
  `down`, no `-v`: the containers and the `brain-test_pgdata` volume, and
  MEP's equivalent, survive, and the next launch's `up --wait` restarts them.
- **"Still in use" is a lock, not a container count.** Each launcher takes a
  shared `flock` on `~/.cache/claude-docker/locks/<container>.lock` *before*
  its `up`, and holds it until the box exits. On exit it tries to turn that
  into an exclusive lock without waiting. Only the last holder gets it, and
  that holder stops the DB. A box that is still between `up` and `docker run`
  (op reads, token probe) already holds the lock, so the DB isn't stopped
  under a box that's still launching. The fd is inherited by `run.sh` and the
  `docker` CLI, so the lock lives exactly as long as the session. A launch
  that starts while a stop is running waits for the stop, then brings the DB
  back up.
- **Stop without compose or op.** The stop is
  `docker stop $(docker ps -q --filter label=com.docker.compose.project=<p>)`,
  with `<p>` read from the container's own compose label. That is
  `compose stop` for every service in the project, with no compose file, no
  `op run` and no 1Password prompt at exit time.
- **Launchers no longer `exec`.** A shared `_lib.sh` helper runs `run.sh` as
  a child, releases or stops on exit, and then `exit`s with the box's status.
  The helper never returns, so the launcher file is never read again after
  the session. That avoids the stale-offset hazard described at the top of
  `run.sh`, which now applies to any launcher that outlives its first read.
- **Signals.** An EXIT trap does the release. INT, TERM and HUP map to
  `exit 128+n` so the trap runs on them too. Under `-it`, Ctrl-C reaches
  `claude` inside the box, not the launcher, so it ends as a normal exit. A
  closed terminal (HUP) and a `kill` (TERM) both run the trap.
- **One helper for both launchers.** `cd_test_db_hold <container>` and
  `cd_test_db_run <container> <run.sh args...>` in `_lib.sh`, keyed by
  container name. Each launcher's existing bring-up block, and its
  abort-vs-warn difference, stays as it is.
- **Visible outcome.** One stderr line on exit, either
  `<container> stopped (last box out)` or `<container> left running: another
  box holds it`. A failed stop warns and doesn't change the box's exit
  status.

Out of scope (deliberately):

- **SIGKILL of the whole process tree** (or a WSL shutdown). No trap runs and
  the DB stays up. That's today's behaviour, and the next launch's `up` is
  unaffected.
- **A box orphaned by its client.** If the `docker` CLI dies but the `--rm`
  container keeps running, the lock is gone and the DB can be stopped under
  that container. Task 4.3 checks whether this happens at all. If it does,
  the container leak is its own problem.
- **A DB started by hand before the first launch.** The launchers own the
  test DB's lifecycle, so it is stopped when the last box exits.
- **Unifying the two bring-up blocks.** They differ on purpose (cd-brain
  aborts, cd-mep warns), and merging them isn't needed for this change.
- **Other launchers.** None of the others start a database.
- **macOS.** Without `flock` the helper warns once at launch and leaves the
  DB running, which is today's behaviour.

## Capabilities

### New Capabilities

- `launchers`: per-project launcher behaviour beyond `run.sh` flags,
  starting with the test-database lifecycle.

### Modified Capabilities

None.

## Impact

- **Code**: `launchers/_lib.sh`, `launchers/cd-brain`, `launchers/cd-mep`.
- **Docs**: `launchers/README.md`. The "Adding one" template keeps `exec`,
  plus a note on test-DB launchers.
- **No `run.sh` change.**
- **Behaviour change**: the test DBs are down between sessions. Host-side
  test runs against them need `docker compose -f compose.test.yml up -d`
  (through `op run`) or a running box.
