## 1. run.sh

- [x] 1.1 Initialize `WITH_MEPDB=0`
- [x] 1.2 Add `--mepdb` to the help heredoc with the default ref on one unbroken line
- [x] 1.3 Add `--mepdb) WITH_MEPDB=1 ;;` to the case statement
- [x] 1.4 Append `POSTGRES_TEST_URL` to `ENV_VARS` when `WITH_MEPDB=1`
- [x] 1.5 Default `CLAUDE_DOCKER_MEPDB_OP_REF` to `op://claude-docker/brain-test-postgres/dsn` with `${VAR-default}` so `""` disables it
- [x] 1.6 op-read fallback for `POSTGRES_TEST_URL` when unset on the host and the ref is non-empty; include in the preflight survey
- [x] 1.7 Append `"mepdb"` to `DOCKER_FLAGS`
- [x] 1.8 `cred_require --mepdb POSTGRES_TEST_URL` (added in 47cd75f)

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record. The a9441e6 commit message records `bash -n`, the help rendering, and docker/op-shim checks for the default ref, an override and `""`.

- [ ] 3.1 Default ref against live 1Password: `claude-docker --mepdb ~/repo` → `psql "$POSTGRES_TEST_URL" -c 'select 1'` succeeds inside the container
- [ ] 3.2 Override ref and `CLAUDE_DOCKER_MEPDB_OP_REF=""` behave as documented
- [ ] 3.3 No-flag invariant: `POSTGRES_TEST_URL` is absent without `--mepdb`
- [ ] 3.4 Fail closed: `--mepdb` with the ref set to `""` and no host var exits non-zero before `docker run`

## 4. Documentation

- [x] 4.1 Credential opt-in and auth-model rows in README
- [x] 4.2 `mepdb` in the statusline-tag list
- [x] 4.3 "myEntryPoint test Postgres (`--mepdb`)" section

## 5. Validation

- [ ] 5.1 `openspec validate add-mepdb-support --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--mepdb`
