<!-- plan version: v1 -->
## 1. Flag

- [x] 1.1 `run.sh`: help, `WITH_NPM_FEED=0`, arg parse, `ENV_VARS+=(NPM_FEED_PASSWORD)`, op preflight, op-read fallback, `DOCKER_FLAGS+=(npm-feed)`, `cred_require`; each next to its `--cis` twin. Proof: `bash -n`; `run.sh --help` lists it.
- [x] 1.2 `cd-ct`, `cd-ws13`: add `--npm-feed`. Proof: `bash -n`.
- [x] 1.3 README rows next to `--cis`.

## 2. Host (owner)

- [ ] 2.1 Store the current `_password` value (base64 PAT) in 1Password; set `CLAUDE_DOCKER_NPM_FEED_OP_REF` in the host env file.
- [ ] 2.2 Replace both `_password` values in `~/.npmrc` with `${NPM_FEED_PASSWORD}`.
- [ ] 2.3 In `cd-ct`, `npm view` of an SBP.Core.UI package succeeds; in a box without the flag, `npm view left-pad version` still works.
