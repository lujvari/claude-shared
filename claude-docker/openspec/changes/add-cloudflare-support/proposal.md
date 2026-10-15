> Retroactive record: implemented in 1fcfdc6 on 2026-09-09 (wrangler v3 pin documented in 06fee53 the same day), written 2026-10-15 to close spec drift.

## Why

`wrangler` and any in-container script that calls the Cloudflare API read
`CLOUDFLARE_API_TOKEN` (and, for tokens spanning more than one account,
`CLOUDFLARE_ACCOUNT_ID`) straight from the environment. The container had no
way to receive them. The alternative, `wrangler login`, is worse: its OAuth
flow needs a host browser, and the token it writes lands under `/root`, the
persistent `claude-code-root` volume, where it outlives every rotation in
1Password. That is the same stale-literal trap `--supabase` was written to
avoid.

## What Changes

- **Add `--cloudflare` opt-in flag** to `run.sh` that forwards
  `CLOUDFLARE_API_TOKEN` and the non-secret `CLOUDFLARE_ACCOUNT_ID` from the
  host when set. No flag → neither reaches the container.
- **1Password fallback for the token only**: when `CLOUDFLARE_API_TOKEN` is
  unset and `CLAUDE_DOCKER_CLOUDFLARE_OP_REF` is set to an
  `op://<vault>/<item>/<field>` reference, `run.sh` runs `op read` on the
  host and forwards the result. `CLOUDFLARE_ACCOUNT_ID` has no op path; it
  belongs in the env file. No built-in default ref.
- **Statusline tag** `cloudflare`.
- **Fail closed** (added in 47cd75f on 2026-09-23): a failed read, or the flag
  ending with no `CLOUDFLARE_API_TOKEN`, aborts before `docker run` unless
  `CLAUDE_DOCKER_OP_OPTIONAL=1`. At introduction a failed read let the launch
  continue.
- **No mount, no `wrangler login`, no git credential injection.** Token-only
  is the whole auth path.
- **Help and README tell users to run `npx wrangler@3`**: the image ships
  Node 20 and wrangler 4.x requires Node >= 22, so a bare `npx wrangler`
  fails before it reads the token and looks like a broken flag.

Out of scope (deliberately):

- Raising the image's `NODE_VERSION` to 22; the `@3` pin is the documented
  workaround until then.
- Bundling wrangler in the image.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds a Cloudflare credential opt-in.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: `claude-docker/README.md` (opt-in row, auth-model row,
  statusline tag, "Cloudflare and wrangler" section, env-file comment trap).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
- **Dependencies**: none in the image; `op` on the host for the op path.
