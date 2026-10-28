## 0. Owner (blocks 4.x)

- [x] 0.1 Item `brain-cf-access` in vault `claude-docker` (renamed by the
      owner from its copied title `claude-docker`). Fields: `username` is the
      Client ID (39 chars, ends `.access`), `credential` is the Client Secret.
      The `run.sh` defaults point at those labels.
- [x] 0.2 Labels checked from WSL, printing labels, lengths and suffix only

## 1. run.sh

- [x] 1.1 `WITH_BRAIN=0`, a `--brain)` case, `CLAUDE_DOCKER_BRAIN=1` sets
      `WITH_BRAIN=1`, and a help entry naming both default refs
- [x] 1.2 `BRAIN_CF_ID_OP_REF` / `BRAIN_CF_SECRET_OP_REF` with `${VAR-default}`
      defaults, a preflight entry, and an `op_read` fallback when the host var
      is unset
- [x] 1.3 Add both vars to `ENV_VARS`, `brain` to `DOCKER_FLAGS`, and
      `cred_require --brain` for both vars
- Proof: `bash -n run.sh`; `--help` lists `--brain` and both refs

## 2. entrypoint.sh

- [x] 2.1 Before `exec`: if both vars are set and `claude mcp get brain`
      fails, run `claude mcp add-json --scope user brain` with the
      placeholder JSON. Quote it so the shell does not expand `${...}`.
      A seeding failure warns and does not abort (`set -eu`).
- Proof: in a throwaway HOME, run the block twice, then check that
  `claude mcp get brain` shows the literal placeholders and that there is
  exactly one entry

## 3. Launchers and docs

- [x] 3.1 `_lib.sh`: `export CLAUDE_DOCKER_BRAIN="${CLAUDE_DOCKER_BRAIN:-1}"`
- [x] 3.2 README rows: flag table, auth model, statusline tag, token-probe
      "not checked". Add `--brain` to `openspec/specs/cli-help/spec.md`.

## 4. Live proof (after 0.x)

- [x] 4.0 Rebuild the image (`docker build -t claude-code:local <claude-docker>`).
      entrypoint.sh is baked in at build, and run.sh never rebuilds, so a stale
      image forwards the vars but never seeds the entry.
- [x] 4.1 Relaunch `cd-brain`, then `claude mcp list` shows `brain` connected
- [x] 4.2 A `list` tools call to `brain` returns. The DB is empty, so an
      empty result is fine.
- [x] 4.3 `curl -s -o /dev/null -w '%{http_code}' https://brain.karansjet.dev/mcp`
      returns 403
- [ ] 4.4 Fail closed: `CLAUDE_DOCKER_BRAIN_CF_ID_OP_REF=op://claude-docker/nope/x`
      with `--brain` exits non-zero before `docker run`
- [x] 4.5 Post to the host: the op-ref item and fields, the env var names, and
      which launch shows Brain. No values.
