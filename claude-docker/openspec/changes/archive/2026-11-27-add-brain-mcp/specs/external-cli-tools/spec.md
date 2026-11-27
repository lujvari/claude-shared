## ADDED Requirements

### Requirement: Brain MCP opt-in

`run.sh` SHALL accept `--brain`, and SHALL treat `CLAUDE_DOCKER_BRAIN=1` the
same way. Either one resolves `BRAIN_CF_ACCESS_CLIENT_ID` and
`BRAIN_CF_ACCESS_CLIENT_SECRET` and forwards them into the container. Values
SHALL come from the host environment, or else from
`CLAUDE_DOCKER_BRAIN_CF_ID_OP_REF` / `CLAUDE_DOCKER_BRAIN_CF_SECRET_OP_REF`,
which default to refs in the `claude-docker` vault. No secret value SHALL
appear in any committed file or in `~/.claude.json`.

#### Scenario: Launcher with default refs
- GIVEN the item `brain-cf-access` exists in vault `claude-docker`
- WHEN a `cd-*` launcher starts a box
- THEN both vars are set in the box
- AND `claude mcp list` shows `brain` connected
- AND a tools call (`list`) to `brain` succeeds

#### Scenario: Refs do not resolve
- GIVEN `--brain` and a ref that `op read` cannot resolve
- WHEN `run.sh` reaches the credential post-check
- THEN it exits non-zero before `docker run` and names `--brain`

#### Scenario: Plain run.sh without the flag
- WHEN `run.sh` runs without `--brain` and without `CLAUDE_DOCKER_BRAIN=1`
- THEN neither var reaches the container

### Requirement: Brain MCP entry seeded with placeholders

When both vars are non-empty, `entrypoint.sh` SHALL make sure a user-scope
HTTP MCP entry named `brain` exists for `https://brain.karansjet.dev/mcp`.
Its headers SHALL be the literal placeholders
`CF-Access-Client-Id: ${BRAIN_CF_ACCESS_CLIENT_ID}` and
`CF-Access-Client-Secret: ${BRAIN_CF_ACCESS_CLIENT_SECRET}`. The entrypoint
SHALL NOT remove an existing entry.

#### Scenario: Idempotent relaunch
- GIVEN the entry already exists
- WHEN a box starts again
- THEN the entry is left as it is, and the box still starts

#### Scenario: Endpoint rejects unauthenticated calls
- WHEN a request without the CF-Access headers is sent to the endpoint
- THEN it gets 403
