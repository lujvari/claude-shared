<!-- plan version: v1 -->
## 1. Flag

- [x] 1.1 `run.sh`: help text, `WITH_CIS=0`, arg parse, `ENV_VARS+=(CIS_API_KEY)`, op-needed preflight, op-read fallback, `DOCKER_FLAGS+=(cis)`, `cred_require --cis CIS_API_KEY`; each next to its `--sonar` twin. Proof: `bash -n run.sh`; `run.sh --help | grep -c CIS` ≥ 2.
- [x] 1.2 `launchers/cd-cis`: add `--cis`. Proof: `bash -n`.
- [x] 1.3 README flag table, if it lists `--sonar`.

## 2. Host (owner)

- [x] 2.1 Store the key in 1Password; set `CLAUDE_DOCKER_CIS_OP_REF` in the host env file.
- [x] 2.2 Change the `cis-local` env in `~/.claude.json` to `"${CIS_API_KEY}"`, and the Supabase one to `"${SUPABASE_ACCESS_TOKEN}"`.
- [ ] 2.3 `cd-cis`: `/mcp` shows `cis-local` connected; a box without `--cis` shows no literal key in `~/.claude.json` (`grep -c CIS_API_KEY` finds only the reference).
