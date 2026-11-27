> Retroactive record: implemented in a9441e6 on 2026-09-15, written 2026-10-15 to close spec drift.

## Why

The myEntryPoint test suite reads its database from `POSTGRES_TEST_URL`.
Sessions run the suite inside the container, which has no `op` and no
1Password identity, so the DSN had to be resolved on the host and handed in
at launch. Without it the Postgres-gated tests are skipped, which reads as a
pass.

Unlike the other credential flags, `--mepdb` names one specific database
rather than a class of service, so an env var the user must set to exactly
one value is ceremony, not configuration. The op-ref is therefore defaulted.

## What Changes

- **Add `--mepdb` opt-in flag** to `run.sh` that forwards
  `POSTGRES_TEST_URL` from the host when set. No flag → the variable does not
  reach the container.
- **Defaulted 1Password fallback**: when `POSTGRES_TEST_URL` is unset,
  `run.sh` reads `CLAUDE_DOCKER_MEPDB_OP_REF`, which defaults to
  `op://claude-docker/brain-test-postgres/dsn` (`${VAR-default}` form).
  Setting the variable to another ref overrides it; setting it to `""`
  switches the 1Password path off.
- **Statusline tag** `mepdb`.
- **Fail closed** (added in 47cd75f on 2026-09-23 — the incident that
  motivated the gate was a `--mepdb` launch whose read failed silently): a
  failed read, or the flag ending with no `POSTGRES_TEST_URL`, aborts before
  `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1`.
- **No mount and no git credential injection.**
- **README**: opt-in row, auth-model row, statusline tag, and a
  "myEntryPoint test Postgres" section explaining the defaulted ref and that
  a DSN, unlike a token, has no scope to narrow: the item must point at a
  disposable test instance.

Out of scope (deliberately):

- Any database-side hardening; the mitigation is keeping the item pointed at
  a throwaway instance whose role has rights on the test database only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds the myEntryPoint test-database opt-in.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
- **Unverified at introduction**: the a9441e6 commit message records that the
  default ref was exercised against op shims, not against live 1Password.
