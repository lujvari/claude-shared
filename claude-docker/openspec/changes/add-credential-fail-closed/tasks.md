## 1. run.sh

- [x] 1.1 `op_read` appends each failed ref to `$OP_FAIL_LOG`
- [x] 1.2 The "which flags need op" survey runs whether or not `op` is on PATH; a missing `op` aborts
- [x] 1.3 A failed `op whoami` preflight aborts and suppresses the per-ref reads
- [x] 1.4 Post-condition gate after all credential blocks: `$OP_FAIL_LOG` non-empty, or `cred_require` finds a flag with no credential, aborts
- [x] 1.5 `CLAUDE_DOCKER_OP_OPTIONAL=1` downgrades every abort to a warning

## 2. Smoke tests

Not run as part of this retroactive record.

- [ ] 2.1 `--mepdb` with `CLAUDE_DOCKER_MEPDB_OP_REF=""` and no host var exits non-zero before `docker run`
- [ ] 2.2 The same launch with `CLAUDE_DOCKER_OP_OPTIONAL=1` starts, without `POSTGRES_TEST_URL`
- [ ] 2.3 An expired service-account token aborts with one preflight message, not one per ref

## 3. Documentation

- [x] 3.1 Mark the superseded "silent" clauses in the base spec and the older change specs
- [x] 3.2 Some `run.sh` comments still say "Silent on failure" (e.g. the `--gh` op-ref fallback)

## 4. Validation

- [ ] 4.1 `openspec validate add-credential-fail-closed --strict` exits 0 (not run)
