> Retroactive record: implemented in 0a1dd4a on 2026-10-07, written 2026-10-15 to close spec drift.

Follow-ups the same day: d385738 repaired a mangled character in the README
row; 96e3f13 dropped the `cd-ct --admin` alias that 0a1dd4a had added, in
favour of passing `--ado-admin` directly.

## Why

Some Azure DevOps work (service connections, service accounts) needs an
elevated PAT. Putting that PAT in `AZURE_DEVOPS_EXT_PAT` would give every
routine call — the git credential helper, `az devops` — admin rights. The
elevated token needs its own variable that only calls naming it explicitly
will use, and its own opt-in so a routine session never holds it.

## What Changes

- **Add `--ado-admin` opt-in flag** to `run.sh` that forwards
  `AZURE_DEVOPS_ADMIN_PAT` from the host when set, alongside (not instead of)
  `--ado`'s `AZURE_DEVOPS_EXT_PAT`. No flag → the variable does not reach the
  container.
- **1Password fallback** via `CLAUDE_DOCKER_ADO_ADMIN_OP_REF`
  (`op://<vault>/<item>/<field>`). No built-in default ref.
- **Deliberately not wired into git or `az devops`**: the credential helper
  and `az` keep the everyday PAT; admin rights apply only where a caller
  names `AZURE_DEVOPS_ADMIN_PAT`. Usually paired with `--ado`, but not
  required to be.
- **Statusline tag** `ado-admin`.
- **Fail closed**: `cred_require --ado-admin AZURE_DEVOPS_ADMIN_PAT`; a failed
  read or no token aborts before `docker run` unless
  `CLAUDE_DOCKER_OP_OPTIONAL=1`.
- **README**: credential opt-in row and auth-model row.

Out of scope (deliberately):

- A launcher alias (`cd-ct --admin` existed briefly and was removed in
  96e3f13).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds an elevated Azure DevOps PAT opt-in, separate
  from `--ado`.

## Impact

- **Code**: `claude-docker/run.sh`; `claude-docker/launchers/cd-ct` (alias
  added in 0a1dd4a, removed in 96e3f13).
- **Docs**: `claude-docker/README.md` (opt-in and auth-model rows; the
  statusline-tag list and threat-model bullet were not updated).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.** `--ado` is unchanged.
