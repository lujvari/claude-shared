## Why

Brain plan 0001 phase 3: every box should reach the remote Brain MCP at
`https://brain.karansjet.dev/mcp`. It sits behind Cloudflare Access service
auth, so each request carries a `CF-Access-Client-Id` and
`CF-Access-Client-Secret` header. The host already reaches it through a
`headersHelper`. Boxes get the same server from env vars resolved at launch,
which follows the repo's other credentials.

## What Changes

- **`--brain` flag** in `run.sh`. It resolves `BRAIN_CF_ACCESS_CLIENT_ID` and
  `BRAIN_CF_ACCESS_CLIENT_SECRET` and forwards them into the container. A host
  value wins. Otherwise `run.sh` reads `CLAUDE_DOCKER_BRAIN_CF_ID_OP_REF` and
  `CLAUDE_DOCKER_BRAIN_CF_SECRET_OP_REF`, which default to
  `op://claude-docker/brain-cf-access/username` and `.../credential`
  (`${VAR-default}` form, so an empty value switches 1Password off).
- **On for every launcher.** `launchers/_lib.sh` exports
  `CLAUDE_DOCKER_BRAIN=1`, the same way it exports the bus dir, and `run.sh`
  treats that as `--brain`. Plain `run.sh` stays opt-in.
- **Fails closed.** The flag gets a preflight entry and
  `cred_require --brain` on both vars. A launch whose refs don't resolve exits
  before `docker run`. `CLAUDE_DOCKER_OP_OPTIONAL=1` is the existing escape.
- **MCP entry seeded by `entrypoint.sh`.** When both vars are non-empty and
  `claude mcp get brain` finds nothing, it runs
  `claude mcp add-json --scope user brain '<json>'`. The JSON is an HTTP entry
  whose headers are the literal placeholders `${BRAIN_CF_ACCESS_CLIENT_ID}`
  and `${BRAIN_CF_ACCESS_CLIENT_SECRET}`. `~/.claude.json` lives in the
  shared `claude-code-root` volume, so only placeholders land on disk, and
  rotating the token needs no change there. The entrypoint never removes the
  entry, because another box running at the same time may be using it.
  Writing through `claude mcp` rather than `jq` leaves the file to Claude
  Code's own writer.
- **Statusline tag** `brain`, a token-probe "not checked" entry, README rows,
  and the `cli-help` flag list.

Verified 2026-10-28 on the box's Claude Code 2.1.304, using a local listener
and a throwaway HOME. `${VAR}` in the `headers` of a user-scope HTTP entry is
expanded. With the vars unset, Claude Code warns
`Missing environment variables` and sends the literal `${...}`. Brain answers
that with a 403, so a box launched without `--brain` fails visibly and leaks
nothing.

Out of scope:
- Copying the service token from vault `brain` to vault `claude-docker`. The
  owner does that by hand.
- Granting the box service account access to vault `brain`. It never gets it.
- The host-side entry.
- Brain itself.

## Capabilities

### Modified Capabilities

- `external-cli-tools`: adds the Brain MCP opt-in and its seeded entry.
- `cli-help`: `--brain` joins the wrapper-flag list.

## Impact

- **Code**: `claude-docker/run.sh`, `claude-docker/entrypoint.sh`,
  `claude-docker/launchers/_lib.sh`.
- **Docs**: `claude-docker/README.md`, `openspec/specs/cli-help/spec.md`.
- **Behaviour change**: every `cd-*` launch now needs the Brain item to
  resolve, or it is blocked.
