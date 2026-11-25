## Why

`~/.npmrc` on the shared `claude-code-root` volume holds the sbp-controltower
`SBP.Core.UI` feed credential as two literal `_password` lines, so every box
reads it, other clients' boxes included (found 2026-11-24). Only the CT boxes
(`cd-ct`, `cd-ws13`) need it. npm expands `${VAR}` in `.npmrc`; with the
variable unset, npm leaves that one registry unauthenticated and works
normally for every other registry (checked on npm 10.8.2).

Whether the `--ado` PAT has Packaging (Read) scope is unknown, so the feed
credential gets its own source instead of being derived from it.

## What Changes

- New `--npm-feed` flag: forward `NPM_FEED_PASSWORD` (the value `.npmrc`
  `_password` takes, i.e. the base64-encoded PAT), from the host env or
  `op read "$CLAUDE_DOCKER_NPM_FEED_OP_REF"`. Same shape as `--sonar`.
- `cd-ct` and `cd-ws13` pass `--npm-feed`.
- Owner-side: both `_password` lines in `~/.npmrc` become
  `_password=${NPM_FEED_PASSWORD}`; the op-ref goes in the host env file.

## Out of scope

- Deriving the password from `AZURE_DEVOPS_EXT_PAT`.
- Feeds other than the one `.npmrc` already names.
