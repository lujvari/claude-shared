> Retroactive record: implemented in 8551b47 on 2026-09-08, written 2026-10-15 to close spec drift.

## Why

The official Supabase MCP server reads its credential from
`SUPABASE_ACCESS_TOKEN`. Before this flag the only way to give an
in-container MCP server that token was to paste the personal access token
as a literal into the server's `env` block in `~/.claude.json`. That file
lives in the persistent `claude-code-root` volume, so the literal survives
every relaunch and cannot see a rotation in 1Password: after a rotation the
sandbox keeps answering `401 Unauthorized` with a token that no longer
exists, and restarting never helps because the literal *is* the source.

Claude Code expands `${VAR}` in an MCP `env` value from the container
environment when it spawns the server, so forwarding the token as an env
var at launch and referencing `"${SUPABASE_ACCESS_TOKEN}"` from the MCP
entry makes 1Password the single source, re-read on every launch.

## What Changes

- **Add `--supabase` opt-in flag** to `run.sh` that forwards
  `SUPABASE_ACCESS_TOKEN` from the host when set. No flag → the variable
  does not reach the container.
- **1Password fallback**: when `SUPABASE_ACCESS_TOKEN` is unset on the host
  and `CLAUDE_DOCKER_SUPABASE_OP_REF` is set to an `op://<vault>/<item>/<field>`
  reference, `run.sh` runs `op read` on the host and forwards the result.
  No built-in default ref.
- **Statusline tag** `supabase` in `CLAUDE_DOCKER_FLAGS`.
- **Fail closed** (added later, in 47cd75f on 2026-09-23, for every
  credential flag): a failed `op read`, or `--supabase` ending up with no
  `SUPABASE_ACCESS_TOKEN`, aborts the launch before `docker run` unless
  `CLAUDE_DOCKER_OP_OPTIONAL=1`. At introduction the flag was silent on
  failure.
- **No git credential injection** and no mount: Supabase is an API, not a
  git host.
- **README**: credential opt-in row, auth-model row, statusline tag, and a
  "Supabase MCP server" section showing the MCP entry with
  `"${SUPABASE_ACCESS_TOKEN}"` and warning against a pasted literal.

Out of scope (deliberately):

- Registering the MCP server itself; that stays user-scope config.
- The RingRecipe end-user test logins, which are a different credential
  with a different blast radius (see `add-rr-e2e-support`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds a Supabase credential opt-in. The
  credentials-opt-in invariant holds: nothing reaches the container without
  the flag.

## Impact

- **Code**: `claude-docker/run.sh` (flag parse, help entry, `ENV_VARS`,
  op-read fallback, statusline tag; later `cred_require`).
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes**; purely additive and gated.
- **Dependencies**: none in the image. `op` is needed on the host only when
  the op-ref path is used.
