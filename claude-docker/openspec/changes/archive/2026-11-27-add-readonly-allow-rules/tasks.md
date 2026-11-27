## 1. Seed

- [x] 1.1 `examples/settings.docker.json`: add `permissions.allow` with the three rules in the proposal, before `deny`. `python3 -m json.tool` parses it.

## 2. Docs

- [x] 2.1 README.md, the `settings.docker.json` paragraph: one sentence on the allow list (the box's own config only; Claude Code already allows plain read-only commands in the workspace).

## 3. Proof in the box

`claude -p` with `--permission-mode default --strict-mcp-config --model haiku --output-format json`, from an empty scratch directory (no project settings), with `--settings` holding `disableAllHooks` plus, for the second run, the example's `permissions` block. The box's own live seed still applies underneath. `permission_denials` lists what would have prompted or was denied.

- [x] 3.1 Without the rules: `ls ~/.claude/skills`, `head -2 ~/.claude/skills/agent-bus/SKILL.md`, `ls ~/.inat/rules` and a Read-tool read of `~/.claude/CLAUDE.md` are denied.
- [x] 3.2 With the rules: those four run, and `python3 -c "print(1)"` is still denied. Deny over allow: the allowed dirs are read-only mounts with no `.env` to read, so a scratch dir stands in: with `Read(//<scratch>/**)` allowed and the example's deny list, the Read tool reads `<scratch>/sub/ok.txt` and is denied `<scratch>/sub/.env`.

## 4. Host (control session, owner's OK)

- [x] 4.1 Merge the three rules into the host's `~/.claude/settings.docker.json` `permissions.allow`, keeping its existing entries.

## 5. Validation and hand-off

- [x] 5.1 `openspec validate add-readonly-allow-rules --strict` exits 0.
- [x] 5.2 Commit to `main` and push.
- [x] 5.3 Post 4.1 to the host as a reply on `20261120T085701Z-d9ee4a`.
