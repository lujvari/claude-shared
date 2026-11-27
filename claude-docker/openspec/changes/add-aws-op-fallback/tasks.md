## 1. run.sh

- [x] 1.1 Extend the `--aws` help-heredoc entry to mention the 1Password fallback (`CLAUDE_DOCKER_AWS_OP_REF` resolves canonical sub-fields)
- [x] 1.2 Add a new gated block beside the `--ado` / `--jira` OP fallbacks: when `WITH_AWS=1`, `AWS_ACCESS_KEY_ID` unset, and `CLAUDE_DOCKER_AWS_OP_REF` set, call `op read "$ref/access_key_id"` and `op read "$ref/secret_access_key"`; on both non-empty, forward as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (export + append `-e` to `ENV_ARGS`)
- [x] 1.3 In the same block, optionally read `$ref/session_token` and forward as `AWS_SESSION_TOKEN` when non-empty
- [x] 1.4 In the same block, optionally read `$ref/region` and forward as `AWS_REGION` — only when `AWS_REGION` is not already set on the host (host env wins)
- [x] 1.5 Tolerate a trailing `/` on `CLAUDE_DOCKER_AWS_OP_REF` (strip with `${var%/}`)
- [x] 1.6 Silent on `op` missing / sign-out / item-absent — matches `--ado` / `--jira` failure mode
- [x] 1.7 Update the existing `--aws` mount-block comment to cross-reference the new OP fallback block
- [x] 1.8 No changes to `DOCKER_FLAGS`: the `aws` statusline tag is already emitted whenever `WITH_AWS=1`, regardless of credential source

## 2. entrypoint.sh

- [x] 2.1 No changes. AWS access is not git-host auth; no `inject_insteadof` call is added. The forwarded env vars are read directly by in-container `aws` CLI calls.

## 3. Smoke tests

- [x] 3.1 `docker build -t claude-code:local ./claude-docker` succeeds (no Dockerfile changes — sanity rebuild only)

## 4. Documentation

- [x] 4.1 Extend the `--aws` row in the Credential opt-in table to describe `CLAUDE_DOCKER_AWS_OP_REF` and the field-name convention
- [x] 4.2 Extend the `--aws` row in the Auth model table to mention the OP fallback and clarify it covers static keys (not SSO)
- [x] 4.3 Add a "Static keys via 1Password (`--aws`)" subsection alongside the existing "AWS SSO flow (`--aws`)" section with an example invocation and the field-name list
- [x] 4.4 No new entry in the statusline-tag list: the `aws` tag already covers this flag regardless of credential source

## 5. Validation

- [x] 5.1 `openspec validate add-aws-op-fallback --strict` exits 0
- [x] 5.2 `claude-docker --help` shows the extended `--aws` description including `CLAUDE_DOCKER_AWS_OP_REF`
- [x] 5.3 Spot-check that the `--ephemeral` interaction is a no-op: the OP fallback only sets env vars (no named-volume writes), so `--aws --ephemeral` is functionally identical to `--aws` for the credential path; ephemerality continues to govern OAuth/history persistence orthogonally
- [x] 5.4 Spot-check `--aws` composition with other flags: the new block runs after the unified `ENV_VARS` forwarding loop and appends to `ENV_ARGS`, so combined invocations like `claude-docker --aws --gh --jira ~/repo` are unaffected (each flag's fallback block is independent)

## 6. Before archive

- [ ] 6.1 The spec delta describes the old design (host `AWS_*` env forwarded into the box) and the main spec `openspec/specs/external-cli-tools/spec.md` has no op-ref text at all. Decide first: the Aegon key is revoked (5f20562), so either delete the `CLAUDE_DOCKER_AWS_OP_REF` / `CLAUDE_DOCKER_AWS_STATIC_*` path from `run.sh` and archive this change with `--skip-specs`, or rewrite the delta's MODIFIED "Credentials opt-in" to the current behaviour (op-ref → `~/.aws/credentials` profile written by `entrypoint.sh`) starting from the main spec's text, then archive normally. Pass: `openspec validate --all` clean and the main spec matches `run.sh`.
