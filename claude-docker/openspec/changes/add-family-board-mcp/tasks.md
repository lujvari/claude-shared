## 1. entrypoint.sh

- [x] 1.1 Factor the brain block into a `seed_access_mcp <name> <url>` helper; call it for `brain` and `family-board`

Proof: `bash -n entrypoint.sh`; the helper run with a stub `claude` and a scratch `$HOME` adds both entries with literal placeholders, skips an existing one, and only warns when `claude` fails.

## 2. Documentation

- [x] 2.1 README: section retitled, family-board entry and shared-token note; `--brain` table row mentions family-board

## 3. Live (host, owner)

- [ ] 3.1 Rebuild the image, relaunch a `cd-*` box: `claude mcp get family-board` -> Connected, `tools/list` returns 16 tools, no secret values in output
