## Why

Brain (laslo/brain) needs a real Postgres for its phase 1 tests, and a box
cannot run one. The owner chose (2026-10-23) to follow the `--mepdb` pattern:
a `laslo_brain_test` database and role on the same host test Postgres, with the DSN
held in 1Password and forwarded at launch.

## What Changes

- **Add `--braindb` opt-in flag** to `run.sh` that forwards `BRAIN_TEST_DSN`
  from the host when set. No flag → the variable does not reach the container.
- **Defaulted 1Password fallback**: when `BRAIN_TEST_DSN` is unset, `run.sh`
  reads `CLAUDE_DOCKER_BRAINDB_OP_REF`, which defaults to
  `op://claude-docker/laslo-brain-test-postgres/dsn` (`${VAR-default}` form).
  The `laslo-` prefix is there because `brain-test-postgres` is already
  myEntryPoint's item.
- **Own variable name**, not a second `POSTGRES_TEST_URL`, so `--mepdb` and
  `--braindb` on one launch cannot collide.
- **Statusline tag** `braindb`, **fail closed** via `cred_require`, preflight
  entry — all as for `--mepdb`.
- **`cd-brain`** bakes in `--braindb`.
- **README**: opt-in row, auth-model row, statusline tag, a paragraph under
  the myEntryPoint test Postgres section, and the token-probe "not checked" list.

Out of scope: creating the `laslo_brain_test` database and role, and the 1Password
item. Both are host-side steps for the owner; nothing in this repo provisions
the test Postgres.

## Capabilities

### Modified Capabilities

- `external-cli-tools`: adds the Brain test-database opt-in.
- `cli-help`: `--braindb` joins the wrapper-flag list.

## Impact

- **Code**: `claude-docker/run.sh`, `claude-docker/launchers/cd-brain`.
- **Docs**: `claude-docker/README.md`.
- **No breaking changes.**
