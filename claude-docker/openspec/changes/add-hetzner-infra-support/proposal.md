> Retroactive record: implemented in 84b1ec7 on 2026-10-09, written 2026-10-15 to close spec drift.

Follow-up: a4dcd30 (2026-10-10) rejects a token file without the `ops_`
service-account prefix before the read.

## Why

myEntryPoint runs on a Hetzner Cloud VM. Infrastructure work (creating the
server, firewall changes, restore drills) needs `HCLOUD_TOKEN`, which the
`hcloud` CLI and the Terraform/OpenTofu `hcloud` provider read. Day-to-day
work never does.

A Read & Write Hetzner token can delete the live server together with its
backups, so it does not belong in the `claude-docker` vault, which holds only
cheap-to-rotate secrets for disposable resources and is readable by the
everyday service account. It lives in a separate vault that only a second,
read-only service account can see, so a leaked everyday token cannot reach
it.

## What Changes

- **Add `--hetzner-infra` opt-in flag** to `run.sh` that forwards
  `HCLOUD_TOKEN` from the host when set. No flag → the variable does not reach
  the container. No launcher bakes the flag in.
- **Defaulted 1Password fallback with a separate service account**: when
  `HCLOUD_TOKEN` is unset, `run.sh` reads `CLAUDE_DOCKER_HETZNER_OP_REF`
  (default `op://claude-docker-infra/hcloud-mep/token`) with
  `OP_SERVICE_ACCOUNT_TOKEN` taken from the file named by
  `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` (default
  `~/.config/op/infra-service-account-token`), set only inside the subshell
  that performs that one read. Every other flag in the same launch keeps
  reading with the everyday account.
  - Ref set to `""`: 1Password path off.
  - Token-file var set to `""`: the read uses the everyday account instead.
- **Token-file checks**: a missing or empty file, or (a4dcd30) one whose
  content does not start with `ops_`, is reported by path only and recorded
  as a failed ref, which aborts the launch.
- **Preflight independence**: with a token file in use, the flag joins only
  the missing-`op`-binary check, not the everyday `op whoami` preflight, so a
  dead everyday token does not block an infra-only launch. A failed read
  prints a hint that the infra service account was used.
- **Statusline tag** `hetzner-infra`.
- **Fail closed**: `cred_require --hetzner-infra HCLOUD_TOKEN`.
- **No mount and no git credential injection.**
- **README**: opt-in row, auth-model row, statusline tag, threat-model
  mention, and a "Hetzner Cloud infrastructure" section with the one-time
  vault and service-account setup.

Out of scope (deliberately):

- Baking the flag into `cd-mep` or any other launcher.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds a Hetzner Cloud infrastructure opt-in read
  through a second 1Password service account.

## Impact

- **Code**: `claude-docker/run.sh`; `claude-docker/launchers/cd-mep` (touched
  in 84b1ec7).
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
- **Unverified at introduction**: the 84b1ec7 commit message records
  op/docker-shim checks but states the vault, item and service account had
  not been verified against live 1Password.
