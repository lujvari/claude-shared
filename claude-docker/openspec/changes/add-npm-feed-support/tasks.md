<!-- plan version: v2 (see proposal.md) -->
## 1. Flag

- [x] 1.1 `run.sh`: help, `WITH_NPM_FEED=0`, arg parse, `DOCKER_FLAGS+=(npm-feed)`.
- [x] 1.2 `cd-ct`, `cd-ws13`: add `--npm-feed`.
- [x] 1.3 v2: drop the op-ref path (preflight, fallback, host-env forward, `cred_require`); derive `NPM_FEED_PASSWORD` from `AZURE_DEVOPS_EXT_PAT` after the ADO block; abort without `--ado`. Help and README match. Proof: `bash -n`; the derive snippet run on a fake PAT gives the same bytes as Python's base64; `run.sh --npm-feed` without `--ado` aborts.

## 2. Host (owner)

- [x] 2.1 Both `_password` values in `~/.npmrc` are `${NPM_FEED_PASSWORD}`.
- [ ] 2.2 Remove the v1 leftovers: the `ct-npm-feed` 1Password item (expired PAT) and the `CLAUDE_DOCKER_NPM_FEED_OP_REF` line in the host env file.
- [ ] 2.3 In `cd-ct`, `npm view @achrinza/node-ipc version` succeeds; in a box without the flag, `npm view left-pad version` still works.
