## 1. run.sh

- [x] 1.1 Initialize `WITH_BUS=1`; add `--no-bus) WITH_BUS=0 ;;` to the case statement
- [x] 1.2 Add `--no-bus` to the help heredoc and `CLAUDE_DOCKER_BUS_DIR` to the Environment section
- [x] 1.3 Derive the key from the first workspace relative to the bus dir's parent (`/` → `.`), else its basename
- [x] 1.4 Reject unsafe keys (empty, leading `.`, characters outside `A-Za-z0-9._-`) with a warning and no mount
- [x] 1.5 Warn and skip when `CLAUDE_DOCKER_BUS_DIR` is set but missing
- [x] 1.6 `mkdir -p <bus>/<key>/in <bus>/<key>/out`; mount `<bus>/<key>` at `/bus` and `<bus>/<key>/in` at `/bus/in:ro`
- [x] 1.7 Set `AGENT_BUS_DIR`, `AGENT_BUS_SELF`, `SLACK_OUTBOX_QUEUE`

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Launchers and examples

- [x] 3.1 `launchers/_lib.sh` defaults `CLAUDE_DOCKER_BUS_DIR` to `<dev-root>/.agent-bus`
- [x] 3.2 `examples/settings.docker.json` wires the agent-bus hooks

## 4. Smoke tests

Not run as part of this retroactive record; the 2a666b0 commit message records no verification.

- [ ] 4.1 With an existing bus dir, a box sees only its own `/bus`; writing under `/bus/in` fails, writing under `/bus/out` succeeds
- [ ] 4.2 Two boxes with different first workspaces cannot see each other's mailbox
- [ ] 4.3 `--no-bus` mounts nothing and sets no `AGENT_BUS_*` variable
- [ ] 4.4 Missing bus dir and unsafe key each warn and launch without a mailbox
- [ ] 4.5 Mailbox is present under `--ro` and `--ephemeral`

## 5. Documentation

- [x] 5.1 `--no-bus` row in the README hardening-flags table
- [ ] 5.2 Help and README mention `AGENT_BUS_DIR` / `AGENT_BUS_SELF` and the warn-and-skip cases (not done)

## 6. Validation

- [ ] 6.1 `openspec validate add-agent-bus-mount --strict` exits 0 (not run)
- [x] 6.2 `claude-docker --help` shows `--no-bus`
