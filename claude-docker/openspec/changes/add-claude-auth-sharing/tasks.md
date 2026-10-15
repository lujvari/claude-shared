## 1. run.sh

- [x] 1.1 Initialize `WITH_CLAUDE_AUTH=0`; add `--claude-auth) WITH_CLAUDE_AUTH=1 ;;` to the case statement
- [x] 1.2 Add `--claude-auth` to the help heredoc, with the security trade-off and `CLAUDE_DOCKER_CONFIG_DIR`
- [x] 1.3 When set and `<config-dir>/.credentials.json` exists, mount it read-write at `/root/.claude/.credentials.json`
- [x] 1.4 When set and the file is missing, print the "run 'claude' and /login on the host first" error and exit 1
- [x] 1.5 Add `auth` to `CLAUDE_DOCKER_FLAGS` when set

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record; the ff89abb commit message records no verification.

- [ ] 3.1 With the flag, a host re-login is picked up inside a running container without a 401
- [ ] 3.2 With the flag and no host credential file, the launch exits 1 before `docker run`
- [ ] 3.3 Without the flag, `/root/.claude/.credentials.json` is not the host file

## 4. Documentation

- [x] 4.1 README documents `--claude-auth`

## 5. Validation

- [ ] 5.1 `openspec validate add-claude-auth-sharing --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--claude-auth`
