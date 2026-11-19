## Why

`--ado` was built for a single Azure DevOps org, the SBP control tower one.
APG work now needs read access to a customer org (`aamnld`, possibly `apgnld`
later) from the `cd-apg` box. The two orgs need two PATs from different
accounts, and an SBP PAT must never end up in a customer box.

`--ado` can already be pointed at another op-ref from a launcher, but every
default leads back to SBP:

- A launcher that forgets the override gets the SBP op-ref from the env file.
- A host `AZURE_DEVOPS_EXT_PAT` wins over any op-ref.
- The git credential helper offers the PAT to every org on `dev.azure.com`,
  so whichever PAT the box holds is sent to any ADO URL it touches.

## What Changes

- **Named ADO profiles.** A launcher sets `CLAUDE_DOCKER_ADO_PROFILE=<name>`.
  Under `--ado`, the profile takes its PAT only from
  `CLAUDE_DOCKER_ADO_<NAME>_OP_REF`, and its orgs from
  `CLAUDE_DOCKER_ADO_<NAME>_ORGS` (comma list).
- **No fallback.** A named profile ignores the host `AZURE_DEVOPS_EXT_PAT`,
  the default op-ref and `CLAUDE_DOCKER_ADO_ORG`. A missing op-ref, a failed
  read or an empty org list aborts the launch. `CLAUDE_DOCKER_OP_OPTIONAL=1`
  does not apply to a named profile.
- **Org-scoped git helper.** Under a named profile, git offers the PAT only to
  `https://dev.azure.com/<org>/…` for the profile's orgs. `run.sh` does this
  through the existing host list, so it holds on old images too.
- **The env file can't select a profile.** `CLAUDE_DOCKER_ADO_PROFILE` is
  honoured only from the launching environment.
- **Persisted `az devops` state is masked.** `~/.azure/azuredevops` and
  `~/.azure-devops` sit in the home volume every box shares. An SBP
  `az devops login` PAT was found there on 2026-11-19, readable from every
  box, and was deleted. From now on that state is visible only to default
  `--ado` boxes.
- **Token probe per org.** Each org in the profile is probed.
- **`--ado-admin` refused whenever a profile is set**, with or without `--ado`. The admin PAT is SBP's, and
  the customer profile has no admin variant.
- **Statusline tag** `ado:<name>` instead of `ado`. A default box can set a display-only `CLAUDE_DOCKER_ADO_LABEL`; `cd-ct` and `cd-ws13` use `ct`.
- **`cd-apg`** gains `--ado` with profile `apg`, org `aamnld`.
- **README**: profiles in the 1Password section, with the hand-over for
  placing the PAT.

No profile set: `--ado` behaves exactly as today. `cd-ct` and `cd-ws13` change
only their tag label.

Out of scope (deliberately):

- One box holding two ADO profiles at once.
- Legacy `<org>.visualstudio.com` hosts under a profile.
- An admin PAT per profile.
- Default `az devops` org configuration.
- Moving SBP onto a named profile, or scoping the default box's helper by
  org. The SBP PAT is still offered to any `dev.azure.com` org from SBP boxes.
- Other persisted credentials in the shared home volume, such as a
  `.git-credentials` backup. That is tracked separately.
- Other `~/.azure` state, such as a future `az login` cache. Only the
  `az devops` paths are masked.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: `--ado` gains named, org-scoped profiles.

## Impact

- **Code**: `claude-docker/run.sh`, new `claude-docker/lib/ado-profile.sh`
  with tests, `claude-docker/lib/token-probe.sh` with its tests,
  `claude-docker/launchers/cd-apg`, and `claude-docker/Dockerfile` (mask
  mountpoints only). The entrypoint does not change.
- **Docs**: `claude-docker/README.md`.
- **Host**: the owner creates the APG PAT (Code: Read, org `aamnld`) and
  stores it in 1Password, installs the launcher with `inat`, and rebuilds the
  image. Only a fresh volume depends on the rebuild.
- **No breaking changes.** Unset profile = current behaviour.
