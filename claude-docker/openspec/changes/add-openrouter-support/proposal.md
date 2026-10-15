> Retroactive record: implemented in 58f03d0 on 2026-09-22, written 2026-10-15 to close spec drift.

## Why

In-container scripts (RingRecipe sessions in particular) need to call the
OpenRouter API, which authenticates with a bearer token read from
`OPENROUTER_API_KEY`. The container had no way to receive it. OpenRouter
ships no CLI, so there is no on-disk login that could serve as a second
source; the token is the whole auth path.

A value handed to `docker run -e` is visible in host process listings and can
reach shell history and session transcripts. OpenRouter spending caps are per
key, so the forwarded key must be a separate low-cap dev key: a leak then
costs one cheap rotation instead of a production rotation plus a redeploy.

## What Changes

- **Add `--openrouter` opt-in flag** to `run.sh` that forwards
  `OPENROUTER_API_KEY` from the host when set. No flag → the variable does not
  reach the container.
- **1Password fallback** via `CLAUDE_DOCKER_OPENROUTER_OP_REF`
  (`op://<vault>/<item>/<field>`), shaped on `--glab` rather than `--gh`:
  host env or op-ref, nothing else. No built-in default ref.
- **Statusline tag** `openrouter`.
- **Fail closed** (added in 47cd75f on 2026-09-23, the next day): a failed
  read, or the flag ending with no `OPENROUTER_API_KEY`, aborts before
  `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1`.
- **`launchers/cd-rr` passes `--openrouter`**, so the flag actually reaches
  RingRecipe sessions.
- **No mount, no CLI fallback, no git credential injection.**
- **README**: opt-in row, auth-model row, statusline tag, and an "OpenRouter"
  section with the two-key (dev vs Worker) split and the `/api/v1/key`
  cap check.

Out of scope (deliberately):

- The production Worker key, which never enters a sandbox.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds an OpenRouter credential opt-in.

## Impact

- **Code**: `claude-docker/run.sh`, `claude-docker/launchers/cd-rr`.
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
