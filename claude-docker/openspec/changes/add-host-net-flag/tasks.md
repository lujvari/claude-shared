## 1. run.sh

- [x] 1.1 Initialize `NETWORK="${CLAUDE_DOCKER_NETWORK:-}"`; add `--host-net) NETWORK=host ;;` to the case statement
- [x] 1.2 Add `--host-net` and `CLAUDE_DOCKER_NETWORK` to the help heredoc, with the MTU symptom and the isolation trade-off
- [x] 1.3 Pass `--network "$NETWORK"` to `docker run` when `NETWORK` is non-empty
- [x] 1.4 Add `net:<network>` to `CLAUDE_DOCKER_FLAGS` when `NETWORK` is non-empty

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record; the eed753a commit message records no verification.

- [ ] 3.1 On a low-MTU VPN, Claude connects with `--host-net` where it fails without it
- [ ] 3.2 `CLAUDE_DOCKER_NETWORK=<name>` attaches the container to that network
- [ ] 3.3 Without the flag or variable, no `--network` argument is passed

## 4. Documentation

- [ ] 4.1 README row for `--host-net` and `CLAUDE_DOCKER_NETWORK` (not done)
- [ ] 4.2 README statusline list mentions `net:<network>` (not done)

## 5. Validation

- [ ] 5.1 `openspec validate add-host-net-flag --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--host-net`
