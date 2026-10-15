## 1. run.sh

- [x] 1.1 Initialize `WITH_OPENROUTER=0`
- [x] 1.2 Add `--openrouter` to the help heredoc, including the low-cap dev-key guidance
- [x] 1.3 Add `--openrouter) WITH_OPENROUTER=1 ;;` to the case statement
- [x] 1.4 Append `OPENROUTER_API_KEY` to `ENV_VARS` when `WITH_OPENROUTER=1`
- [x] 1.5 op-read fallback via `CLAUDE_DOCKER_OPENROUTER_OP_REF`; include in the preflight survey
- [x] 1.6 Append `"openrouter"` to `DOCKER_FLAGS`
- [x] 1.7 `cred_require --openrouter OPENROUTER_API_KEY` (added in 47cd75f)

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Launchers

- [x] 3.1 `launchers/cd-rr` passes `--openrouter`

## 4. Smoke tests

Not run as part of this retroactive record; the 58f03d0 commit message records no verification.

- [ ] 4.1 Host env key is visible inside the container under `--openrouter`
- [ ] 4.2 Op-ref fallback yields a non-empty `OPENROUTER_API_KEY`
- [ ] 4.3 No-flag invariant: the key is absent without `--openrouter`
- [ ] 4.4 Fail closed: no key source → exits non-zero before `docker run`
- [ ] 4.5 In-container `curl` to `https://openrouter.ai/api/v1/key` returns 200 with the key's `limit`

## 5. Documentation

- [x] 5.1 Credential opt-in and auth-model rows in README
- [x] 5.2 `openrouter` in the statusline-tag list
- [x] 5.3 "OpenRouter (`--openrouter`)" section with the two-key table
- [x] 5.4 Threat-model "Exposed" bullet in README lists `OPENROUTER_API_KEY` (done 2026-10-15)

## 6. Validation

- [ ] 6.1 `openspec validate add-openrouter-support --strict` exits 0 (not run)
- [x] 6.2 `claude-docker --help` shows `--openrouter`
