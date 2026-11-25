## ADDED Requirements

### Requirement: family-board MCP entry seeded with placeholders

When `BRAIN_CF_ACCESS_CLIENT_ID` and `BRAIN_CF_ACCESS_CLIENT_SECRET` are both
non-empty, `entrypoint.sh` SHALL make sure a user-scope HTTP MCP entry named
`family-board` exists for `https://family.karansjet.dev/mcp`, with the same
literal placeholder headers as the `brain` entry. The entrypoint SHALL NOT
remove or rewrite an existing entry, and a failure to add it SHALL only warn.

#### Scenario: Fresh box with --brain
- GIVEN `~/.claude.json` has no `family-board` entry
- WHEN a `cd-*` launcher starts a box
- THEN `claude mcp get family-board` shows it connected
- AND its `tools/list` returns the board's tools
- AND `~/.claude.json` holds only the `${VAR}` placeholders

#### Scenario: Idempotent relaunch
- GIVEN the entry already exists
- WHEN a box starts again
- THEN the entry is left as it is, and the box still starts

#### Scenario: Add fails
- WHEN `claude mcp add-json` fails for `family-board`
- THEN the entrypoint prints a warning naming family-board and the box still starts
