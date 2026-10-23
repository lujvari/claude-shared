## 1. run.sh

- [x] 1.1 `WITH_BRAINDB=0`, `--braindb)` case, help entry with the default ref on one line
- [x] 1.2 Append `BRAIN_TEST_DSN` to `ENV_VARS` when set
- [x] 1.3 `BRAINDB_OP_REF` defaulted with `${VAR-default}`; preflight entry; op-read fallback
- [x] 1.4 `braindb` in `DOCKER_FLAGS`; `cred_require --braindb BRAIN_TEST_DSN`

## 2. Launcher

- [x] 2.1 `cd-brain` passes `--braindb`

## 3. brain-test-postgres (owner decision 2026-10-23: dedicated container, not MEP's instance)

- [ ] 3.1 `compose.test.yml` + `.env.test` (op:// refs only) in laslo/brain: postgres:16-alpine, container `brain-test-postgres`, own named volume, `127.0.0.1:47304`, init script creating role `laslo_brain_test` (LOGIN, non-superuser) and the database it owns
- [x] 3.2 `cd-brain` runs `op run --env-file=.env.test -- docker compose -f compose.test.yml up -d --wait` before launching
- [ ] 3.3 Owner: 1Password item `laslo-brain-test-postgres` (claude-docker vault) gets fields `superuser-password` and `dsn` beside the role `password`
- [ ] 3.4 Verify from a box: `host.docker.internal:47304` answers

## 4. Smoke tests

`--mepdb` has no automated tests; these mirror its manual checks.

- [x] 4.1 `bash -n run.sh`; `--help` shows `--braindb` and the default ref
- [ ] 4.2 Live: `cd-brain` → `psql "$BRAIN_TEST_DSN" -c 'select 1'` succeeds in the box
- [x] 4.3 Fail closed: `--braindb` with the ref set to `""` and no host var exits non-zero before `docker run`

## 5. Documentation

- [x] 5.1 README rows, statusline tag, section paragraph, token-probe skip list
