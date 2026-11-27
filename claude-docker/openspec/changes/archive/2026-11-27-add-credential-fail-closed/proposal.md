> Retroactive record: implemented in 47cd75f on 2026-09-23, written 2026-10-15 to close spec drift.

## Why

A `cd-mep` launch on 2026-09-23 came up with `GH_TOKEN` but no
`POSTGRES_TEST_URL`. One `op read` had failed and `op_read` warned on stderr
as designed, but Claude Code then repainted the terminal over the warning.
From inside the container, a skipped credential looks exactly like one that
was never asked for. The myEntryPoint suite skipped 329 Postgres-gated tests,
which reads as a pass.

Until then, each credential flag was specified to "continue silently" when its
token could not be resolved (`--gh`, `--ado`, `--jira`, the `--aws`
1Password fallback). The defect was that policy, not the plumbing.

## What Changes

- **Missing `op` aborts.** When a flag needs 1Password and `op` is not on
  PATH, `run.sh` says so and exits non-zero before `docker run`.
- **Failed preflight aborts.** A failed `op whoami` (expired or revoked
  token, timeout) aborts the launch and suppresses the per-ref reads, so one
  actionable line is not buried under duplicates.
- **Failed read aborts.** `op_read` records every failed ref in
  `$OP_FAIL_LOG`; after all credential blocks, any entry blocks the launch.
- **End-state assertion.** A flag that injected nothing aborts the launch
  even without a failed read, e.g. its `*_OP_REF` set to `""` and no host
  env var. This covers `--gh`, `--glab`, `--ado`, `--ado-admin`, `--jira`,
  `--supabase`, `--cloudflare`, `--openrouter`, `--sonar`, `--mepdb`,
  `--rr-e2e` (either account satisfies it) and `--hetzner-infra`.
- **Escape hatch.** `CLAUDE_DOCKER_OP_OPTIONAL=1` turns every abort above
  into a warning and launches without the missing credentials.
- **Exempt from the end-state assertion:** `--aws`, `--tfe` and `--tofu`.
  They also carry credentials by read-only mount, so an empty env var is the
  normal SSO or on-disk-token case there. A failed `op read` under `--aws`
  still aborts through `$OP_FAIL_LOG`.

This supersedes every "continue silently" clause about an unresolved token in
`specs/external-cli-tools/spec.md` and in the `add-ado-support`,
`add-jira-support` and `add-aws-op-fallback` changes. "Silent" clauses about
absent mounts (`--tfe`, `--tofu`) and host-list enumeration are unaffected.
