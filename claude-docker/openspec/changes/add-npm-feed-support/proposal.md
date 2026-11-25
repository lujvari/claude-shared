<!-- plan version: v2. v1 read a separate feed PAT from 1Password. That PAT
     (from the old ~/.npmrc) had expired, and on 2026-11-25 the cd-ct --ado PAT
     answered 200 on the feed, so v2 derives the password from it instead. -->
## Why

`~/.npmrc` on the shared `claude-code-root` volume held the sbp-controltower
`SBP.Core.UI` feed credential as two literal `_password` lines, so every box
read it, other clients' boxes included (found 2026-11-24). Only the CT boxes
(`cd-ct`, `cd-ws13`) need the feed. npm expands `${VAR}` in `.npmrc` (checked
against a local fake registry); with the variable unset, npm leaves that one
registry unauthenticated and works normally for every other registry (checked
on npm 10.8.2).

The `--ado` PAT those boxes already get can read the feed (HTTP 200 on a
package metadata request, 2026-11-25). Deriving from it keeps one PAT to
rotate instead of two.

## What Changes

- New `--npm-feed` flag. It requires `--ado`, and sets `NPM_FEED_PASSWORD`
  in the box to the base64 of the box's `AZURE_DEVOPS_EXT_PAT`, which is the
  form `.npmrc` `_password` takes.
- `cd-ct` and `cd-ws13` pass `--npm-feed`.
- `~/.npmrc` holds `_password=${NPM_FEED_PASSWORD}` for both feed paths.

## Out of scope

- A separate feed PAT or op-ref.
- Feeds other than the one `.npmrc` already names.
