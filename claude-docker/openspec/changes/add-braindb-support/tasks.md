## 1. run.sh

- [x] 1.1 `WITH_BRAINDB=0`, `--braindb)` case, help entry with the default ref on one line
- [x] 1.2 Append `BRAIN_TEST_DSN` to `ENV_VARS` when set
- [x] 1.3 `BRAINDB_OP_REF` defaulted with `${VAR-default}`; preflight entry; op-read fallback
- [x] 1.4 `braindb` in `DOCKER_FLAGS`; `cred_require --braindb BRAIN_TEST_DSN`

## 2. Launcher

- [x] 2.1 `cd-brain` passes `--braindb`

## 3. Host setup (owner)

- [ ] 3.1 `laslo_brain_test` role (LOGIN, non-superuser) and database it owns, on MEP's `myentrypoint-postgres` (host.docker.internal:47303 from a box). The role lives in the pg-data volume: `docker compose down -v` wipes it, recreate with the same password
- [ ] 3.2 1Password item `laslo-brain-test-postgres` in the `claude-docker` vault, field `dsn`

## 4. Smoke tests

`--mepdb` has no automated tests; these mirror its manual checks.

- [x] 4.1 `bash -n run.sh`; `--help` shows `--braindb` and the default ref
- [ ] 4.2 Live: `cd-brain` → `psql "$BRAIN_TEST_DSN" -c 'select 1'` succeeds in the box
- [x] 4.3 Fail closed: `--braindb` with the ref set to `""` and no host var exits non-zero before `docker run`

## 5. Documentation

- [x] 5.1 README rows, statusline tag, section paragraph, token-probe skip list
