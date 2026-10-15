## 1. run.sh

- [x] 1.1 Initialize `WITH_CLOUDFLARE=0`
- [x] 1.2 Add `--cloudflare` to the help heredoc, including the `npx wrangler@3` note
- [x] 1.3 Add `--cloudflare) WITH_CLOUDFLARE=1 ;;` to the case statement
- [x] 1.4 Append `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` to `ENV_VARS` when `WITH_CLOUDFLARE=1`
- [x] 1.5 op-read fallback for `CLOUDFLARE_API_TOKEN` via `CLAUDE_DOCKER_CLOUDFLARE_OP_REF`
- [x] 1.6 Include the flag in the 1Password preflight survey
- [x] 1.7 Append `"cloudflare"` to `DOCKER_FLAGS`
- [x] 1.8 `cred_require --cloudflare CLOUDFLARE_API_TOKEN` (added in 47cd75f)

## 2. entrypoint.sh

- [x] 2.1 No changes. No git host, no `wrangler login` state to manage.

## 3. Smoke tests

Not run as part of this retroactive record. The 1fcfdc6 commit message records `bash -n`, `run.sh --cloudflare --help`, and a docker-shim check that `docker run` receives the forwarded variables.

- [ ] 3.1 Host env token and account id are both visible inside the container under `--cloudflare`
- [ ] 3.2 Op-ref fallback yields a non-empty `CLOUDFLARE_API_TOKEN`
- [ ] 3.3 No-flag invariant: neither variable reaches the container without `--cloudflare`
- [ ] 3.4 Fail closed: `--cloudflare` with no token source exits non-zero before `docker run`
- [ ] 3.5 `npx wrangler@3 whoami` inside the container authenticates as the token's identity

## 4. Documentation

- [x] 4.1 Credential opt-in and auth-model rows in README
- [x] 4.2 `cloudflare` in the statusline-tag list
- [x] 4.3 "Cloudflare and wrangler (`--cloudflare`)" section: env-file example, wrangler v3 pin, no `wrangler login`, least-privilege token (06fee53)

## 5. Validation

- [ ] 5.1 `openspec validate add-cloudflare-support --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--cloudflare`
