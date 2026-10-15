## 1. run.sh

- [x] 1.1 Initialize `WITH_RR_E2E=0`
- [x] 1.2 Add `--rr-e2e` to the help heredoc with both default item refs
- [x] 1.3 Add `--rr-e2e) WITH_RR_E2E=1 ;;` to the case statement
- [x] 1.4 Append `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `E2E_EMAIL`, `E2E_PASSWORD`, `E2E2_EMAIL`, `E2E2_PASSWORD` to `ENV_VARS` when `WITH_RR_E2E=1`
- [x] 1.5 Default `CLAUDE_DOCKER_RR_E2E_OP_ITEM` / `CLAUDE_DOCKER_RR_E2E2_OP_ITEM` with `${VAR-default}` so `""` disables each
- [x] 1.6 `rr_e2e_fill` helper: host env wins; otherwise read `<item>/username` or `<item>/password`
- [x] 1.7 Preflight survey per account, gated on that account's password being empty and its item set
- [x] 1.8 Append `"rr-e2e"` to `DOCKER_FLAGS`
- [x] 1.9 `cred_require --rr-e2e E2E_PASSWORD E2E2_PASSWORD` (added in 47cd75f)

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record. The 4417697 commit message records a check against live 1Password with a fake `docker` on PATH showing all six variables forwarded.

- [ ] 3.1 `claude-docker --supabase --rr-e2e ~/ringrecipe` then `tool/e2e.sh live` from `Flutter/` passes
- [ ] 3.2 `CLAUDE_DOCKER_RR_E2E2_OP_ITEM=""` launches with only the first account
- [ ] 3.3 No-flag invariant: none of the six variables reach the container without `--rr-e2e`
- [ ] 3.4 Fail closed: both item refs set to `""` and no host passwords → exits non-zero before `docker run`

## 4. Documentation

- [x] 4.1 Credential opt-in and auth-model rows in README
- [x] 4.2 `rr-e2e` in the statusline-tag list
- [x] 4.3 "RingRecipe live E2Es (`--rr-e2e`)" section

## 5. Validation

- [ ] 5.1 `openspec validate add-rr-e2e-support --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--rr-e2e`
