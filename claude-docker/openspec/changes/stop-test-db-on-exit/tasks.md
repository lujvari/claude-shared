## 1. launchers/_lib.sh

- [x] 1.1 `cd_test_db_hold <container>`: `mkdir -p ~/.cache/claude-docker/locks`, open fd 9 on `<container>.lock`, `flock -s -w 60 9`. If `flock` is missing or the wait times out, warn once and record that this launch won't stop the DB.
- [x] 1.2 `cd_test_db_run <container> <run.sh args...>`: install the EXIT trap (release), map INT, TERM and HUP to `exit 130/143/129`, run `"$CD_RUN" "$@"` with `|| rc=$?` (not `exec`), then `exit "$rc"`. It never returns.
- [x] 1.3 Release: `flock -xn 9`. On success, read `com.docker.compose.project` from the container's labels, `docker stop` every running container with that label, and print `stopped (last box out)`. On failure, print `left running: another box holds it`. A failed stop warns and leaves `rc` untouched.
- [x] 1.4 Header comment: why a lock rather than counting containers (the launch-window race), and why the helper exits instead of returning (stale-offset re-read, see the top of run.sh).

## 2. Launchers

- [x] 2.1 `cd-brain`: `cd_test_db_hold brain-test-postgres` before `brain_test_db`, and replace `exec "$CD_RUN" ...` with `cd_test_db_run brain-test-postgres --claude-auth --gh --braindb "$ws" "$@"`. Update the comment block ("leaves it up" becomes "stops it after the last box").
- [x] 2.2 `cd-mep`: the same with `myentrypoint-test-postgres`.

## 3. Docs

- [x] 3.1 `launchers/README.md`: a short "Test-database launchers" note after the template. It covers the hold/run pair, why those launchers don't `exec`, and that the DB is down between sessions.

## 4. Proof

- [x] 4.1 In-box, with shims (no docker in the box): put fake `docker` and `op` on PATH that log their calls, and set `CD_RUN` to a fake that sleeps or exits with a given code. Check:
  (a) a single run logs one `docker stop` and passes the exit code through
  (b) with two overlapping runs, only the second exit stops
  (c) B held at `sleep` before its `docker run`, with A exiting meanwhile, gives no stop
  (d) `kill -HUP` and `kill -TERM` of the launcher stop
  (e) without `flock` on PATH there is a warning and no stop
  Also covered: a launch that starts during a slow stop waits for it, then brings the DB back up. The harness passes 7/7. With the exclusive-lock check broken, 3 tests fail. The harness is a session scratch script and is not committed.
- [x] 4.2 `bash -n` and `shellcheck -s bash -x` (0.11.0, from shellcheck-py in a scratch venv) are clean on `_lib.sh`, `cd-brain` and `cd-mep`. Without `-s bash`, `_lib.sh` raises SC2148 (no shebang), as it already did before this change.
- [x] 4.3 Live on WSL, 2026-11-05: a single `cd-brain` exit stops the DB. With two `cd-brain` boxes (cd-mep shares the helper), the first exit printed `left running: another box holds it` and the second `stopped (last box out)`.
- [x] 4.4 Live on WSL, 2026-11-05: closing a `cd-brain` terminal window stops the DB (`Exited (0)`), and `brain-test_pgdata` survives.
- [ ] 4.5 Live on WSL: after a closed window, check whether the box's own container is left in `docker ps` (an orphan the lock no longer counts).

## 5. Validation

- [x] 5.1 `openspec validate stop-test-db-on-exit --strict` exits 0
