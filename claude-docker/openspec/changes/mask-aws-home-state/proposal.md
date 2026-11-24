## Why

Every box mounts the same `claude-code-root` volume as `/home/claude`. Under
`--aws` with static keys, `entrypoint.sh` writes them to `~/.aws/credentials`
as the `aegon` profile, which lands on that volume. Nothing removes it. On
2026-11-24 the Aegon key (written 2026-11-22) and two `~/.aws/cli/cache` STS
files were readable from every box, client boxes included. The spec already
says a box without `--aws` has no `/root/.aws/`; the implementation broke that.

The same sweep found the secret-read hook does not cover
`~/.azure/azuredevops/personalAccessTokens` or `git credential fill`.

## What Changes

- `run.sh` always tmpfs-masks `/home/claude/.aws` (non-ephemeral boxes),
  owned by the box user. Under `--aws` the `:ro` config and sso binds sit on
  top of it, and `entrypoint.sh` writes the static profile into the tmpfs. AWS
  state no longer touches the volume.
- `hooks/deny-secret-reads.py` denies reading
  `~/.azure/azuredevops/personalAccessTokens` and running
  `git credential fill` / `git credential-store get`.

## Out of scope

- Deleting the stray files already on the volume and rotating what they held.
  That is an ops step the owner runs; the mask only hides `~/.aws`.
- `~/.npmrc` (sbp-controltower feed PAT) and the MCP tokens inline in
  `~/.claude.json`. Both need their own change: relocate behind an opt-in.
- A general "no credential on the shared volume" audit at launch.
