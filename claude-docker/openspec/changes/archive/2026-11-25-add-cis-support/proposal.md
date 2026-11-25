## Why

The `cis-local` MCP server's `CIS_API_KEY` sits as a literal in the user-scope
`~/.claude.json` on the shared `claude-code-root` volume, so every box reads an
SBP key, other clients' boxes included (found 2026-11-24). Claude Code expands
`${VAR}` in user-scope MCP entries, and `--supabase` already follows that
pattern. CIS has no flag to forward the key from, so the literal is the only
way the server gets it today.

## What Changes

- New `--cis` flag: forward `CIS_API_KEY`, from the host env or
  `op read "$CLAUDE_DOCKER_CIS_OP_REF"`. Same shape as `--sonar`: no default
  ref, no mount, end-state assertion, `cis` in `CLAUDE_DOCKER_FLAGS`.
- `cd-cis` passes `--cis`.
- Owner-side (not in the repo): the `cis-local` entry's env becomes
  `"CIS_API_KEY": "${CIS_API_KEY}"`, and `CLAUDE_DOCKER_CIS_OP_REF` goes in the
  host env file. A box without `--cis` then sees the literal `${CIS_API_KEY}`,
  and the server fails to authenticate there.

## Out of scope

- The Supabase literal: `--supabase` already exists; only the `~/.claude.json`
  edit is missing.
- The sbp-controltower npm feed PAT in `~/.npmrc` (separate change).
