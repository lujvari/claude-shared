## 1. run.sh

- [x] 1.1 Initialize `WITH_SUPABASE=0` next to the other opt-in flags
- [x] 1.2 Add `--supabase` to the help heredoc, including the `"${SUPABASE_ACCESS_TOKEN}"` MCP guidance
- [x] 1.3 Add `--supabase) WITH_SUPABASE=1 ;;` to the flag-parsing case statement
- [x] 1.4 Append `SUPABASE_ACCESS_TOKEN` to `ENV_VARS` when `WITH_SUPABASE=1`
- [x] 1.5 When `--supabase` is set, `SUPABASE_ACCESS_TOKEN` is unset, and `CLAUDE_DOCKER_SUPABASE_OP_REF` is set, `op read` the ref on the host and forward the result as `SUPABASE_ACCESS_TOKEN`
- [x] 1.6 Include the flag in the 1Password preflight survey when the op path will be used
- [x] 1.7 Append `"supabase"` to `DOCKER_FLAGS`
- [x] 1.8 Assert the end state with `cred_require --supabase SUPABASE_ACCESS_TOKEN` (added in 47cd75f)

## 2. entrypoint.sh

- [x] 2.1 No changes. No git host, so no credential helper or `insteadOf` rewrite.

## 3. Smoke tests

Not run as part of this retroactive record. The 8551b47 commit message records `bash -n` and `run.sh --supabase --help` checks plus a real-launch check; the items below were never written down as a test plan.

- [ ] 3.1 `SUPABASE_ACCESS_TOKEN=fake claude-docker --supabase ~/repo` → the variable is set inside the container
- [ ] 3.2 Op-ref fallback: with the host var unset and `CLAUDE_DOCKER_SUPABASE_OP_REF` pointing at a readable item, the variable is non-empty inside the container
- [ ] 3.3 No-flag invariant: without `--supabase` the variable is absent inside the container even when set on the host
- [ ] 3.4 Fail closed: `--supabase` with neither source set exits non-zero before `docker run`; `CLAUDE_DOCKER_OP_OPTIONAL=1` launches anyway
- [ ] 3.5 An MCP entry whose env is `"${SUPABASE_ACCESS_TOKEN}"` starts and authenticates

## 4. Documentation

- [x] 4.1 Credential opt-in table row in README
- [x] 4.2 Auth-model table row in README
- [x] 4.3 `supabase` in the statusline-tag list
- [x] 4.4 "Supabase MCP server (`--supabase`)" section with the MCP entry and the no-literal warning

## 5. Validation

- [ ] 5.1 `openspec validate add-supabase-support --strict` exits 0 (not run; this record was written without the openspec CLI)
- [x] 5.2 `claude-docker --help` shows `--supabase`
