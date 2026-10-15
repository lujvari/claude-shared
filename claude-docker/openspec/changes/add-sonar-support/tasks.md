## 1. run.sh

- [x] 1.1 Initialize `WITH_SONAR=0`
- [x] 1.2 Add `--sonar` to the help heredoc, including the user-token-not-analysis-token guidance
- [x] 1.3 Add `--sonar) WITH_SONAR=1 ;;` to the case statement
- [x] 1.4 Append `SONAR_TOKEN` and `SONAR_HOST_URL` to `ENV_VARS` when `WITH_SONAR=1`
- [x] 1.5 op-read fallback for `SONAR_TOKEN` via `CLAUDE_DOCKER_SONAR_OP_REF`; include in the preflight survey
- [x] 1.6 Append `"sonar"` to `DOCKER_FLAGS`
- [x] 1.7 `cred_require --sonar SONAR_TOKEN`

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Launchers

- [x] 3.1 `launchers/cd-ct` passes `--sonar` (3d6a3a8)

## 4. Smoke tests

Not run as part of this retroactive record; the stub-docker checks recorded in 47cd75f cover the gate, not `--sonar` specifically.

- [ ] 4.1 Host env token and host URL are visible inside the container under `--sonar`
- [ ] 4.2 Op-ref fallback yields a non-empty `SONAR_TOKEN`
- [ ] 4.3 No-flag invariant: neither variable reaches the container without `--sonar`
- [ ] 4.4 Fail closed: `SONAR_HOST_URL` alone does not satisfy the flag
- [ ] 4.5 In-container quality-gate status call returns 200 for a known project

## 5. Documentation

- [x] 5.1 Credential opt-in and auth-model rows in README
- [x] 5.2 `sonar` in the statusline-tag list
- [x] 5.3 "SonarCloud (`--sonar`)" section

## 6. Validation

- [ ] 6.1 `openspec validate add-sonar-support --strict` exits 0 (not run)
- [x] 6.2 `claude-docker --help` shows `--sonar`
