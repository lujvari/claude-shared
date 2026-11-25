## Why

family-board (laslo/family-board, its spec 0005) serves an agent MCP at
`https://family.karansjet.dev/mcp` behind Cloudflare Access service auth. The
owner decided (2026-11-24) to reuse the existing per-client tokens: the Access
policy "family-board agents" admits the `claude-docker` service token, the one
boxes already carry for Brain. So boxes need no new credential, only the MCP
entry. The host side is already done.

## What Changes

- **`entrypoint.sh` seeds a user-scope `family-board` MCP entry** beside
  `brain`, under the same condition (both `BRAIN_CF_ACCESS_*` vars set, no
  existing entry), the same `${VAR}` placeholder headers, and the same
  warn-only failure. The two seedings share one helper.
- **README**: the Brain MCP section becomes "Cloudflare Access MCPs" and says
  `--brain`'s token also opens family-board.

Out of scope: renaming the `BRAIN_CF_ACCESS_*` variables (the token is now
shared, but the names are wired through run.sh, 1Password refs and the host;
owner's call, not needed for this); any change to `run.sh` or the launchers.

## Capabilities

### Modified Capabilities

- `external-cli-tools`: a second Access-protected MCP entry from the same token.

## Impact

- **Code**: `claude-docker/entrypoint.sh` (image rebuild needed).
- **Docs**: `claude-docker/README.md`.
- **No breaking changes.** Boxes without `--brain` see a second entry that
  warns about missing variables, exactly as `brain` already does.
