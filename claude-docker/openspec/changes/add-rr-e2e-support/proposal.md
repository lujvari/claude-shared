> Retroactive record: implemented in 4417697 on 2026-09-16, written 2026-10-15 to close spec drift.

## Why

RingRecipe's live-backend E2Es sign in as two fixed test accounts, and
`Flutter/tool/e2e.sh` reads all six values it needs from the environment with
no file fallback — the project's goal is no test password on disk. The suites
run inside the container, which has neither `op` nor any 1Password identity,
so nothing could supply the passwords there. The host has to resolve them at
launch so they exist only in the container's process environment.

## What Changes

- **Add `--rr-e2e` opt-in flag** to `run.sh` that forwards `E2E_EMAIL`,
  `E2E_PASSWORD`, `E2E2_EMAIL`, `E2E2_PASSWORD` and the non-secret
  `SUPABASE_URL` / `SUPABASE_ANON_KEY` from the host when set. No flag → none
  of the six reach the container.
- **Defaulted 1Password fallback for the four account fields.** The refs name
  an *item*, not a field: `CLAUDE_DOCKER_RR_E2E_OP_ITEM` and
  `CLAUDE_DOCKER_RR_E2E2_OP_ITEM`, defaulting to
  `op://claude-docker/RingRecipe e2e account` and
  `op://claude-docker/RingRecipe e2e2 account`. For each account variable that
  is empty on the host, `run.sh` reads `<item>/username` or `<item>/password`.
  Setting either item var to `""` switches that account's 1Password path off.
  The `_OP_ITEM` suffix marks the difference in shape from the `*_OP_REF`
  variables.
- **No 1Password path for `SUPABASE_URL` / `SUPABASE_ANON_KEY`**: neither is a
  secret (the anon key ships in the deployed web bundle); they belong in the
  env file.
- **Statusline tag** `rr-e2e`.
- **Fail closed** (added in 47cd75f on 2026-09-23): a failed read, or the
  flag ending with neither `E2E_PASSWORD` nor `E2E2_PASSWORD`, aborts before
  `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1`. One account may be
  switched off; both may not.
- **Kept separate from `--supabase`**, which forwards an account-wide
  Management-API PAT; these are end-user logins with no admin rights.

Out of scope (deliberately):

- Keeping the values out of process memory: `e2e.sh` passes them as
  `--dart-define`, so they sit in argv and the test bundle. The flag buys
  off-disk, not out-of-memory.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds the RingRecipe live-E2E account opt-in.

## Impact

- **Code**: `claude-docker/run.sh` (`rr_e2e_fill` helper, defaulted item refs,
  per-account preflight survey).
- **Docs**: `claude-docker/README.md` ("RingRecipe live E2Es" section, opt-in
  and auth-model rows, statusline tag).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
