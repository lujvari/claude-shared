## Why

Developers using claude-docker increasingly work in repos hosted on Azure
DevOps (Azure Repos under `dev.azure.com/<org>/<project>/_git/<repo>`).
Today the wrapper has no way to grant in-container `git` access to those
hosts: `--gh` covers GitHub, `--glab` covers GitLab, but Azure DevOps
PATs are not forwarded and `git clone https://dev.azure.com/<org>/...`
fails with `could not read Username for dev.azure.com` mid-session.

Real failure mode observed: Claude tries to fetch an Azure DevOps PR
(e.g. PR 1821 in the SBP.Utility repo) and reports back that it can't
access the host because no PAT is in env or git credential helper. The
user's only workaround today is to pre-clone on the host and pass the
checkout in as a workspace — which loses fetch / pull / `git ls-remote`
access mid-session.

A second, smaller gap: unlike `gh`/`glab`, Azure DevOps PATs aren't
stored in a CLI-tool config file at a stable host path. The `az devops`
extension reads `AZURE_DEVOPS_EXT_PAT` from the environment and stashes
session state in the OS keychain on macOS (not file-mountable). Env-var
forwarding is the only reliable surface here — there is no analogue of
the `gh auth token` host fallback.

## What Changes

- **Add `--ado` opt-in flag** to `run.sh` that forwards
  `AZURE_DEVOPS_EXT_PAT` from the host environment when set. Same shape
  as `--gh`/`--glab`: no flag → no token reaches the container.
- **Forward `CLAUDE_DOCKER_ADO_HOSTS`** (comma-separated host list,
  default `dev.azure.com`) to the container under `--ado`, mirroring the
  existing `CLAUDE_DOCKER_{GITHUB,GITLAB}_HOSTS` pattern. Users with
  legacy `*.visualstudio.com` URLs or self-hosted Azure DevOps Server
  can override by exporting the env var before running.
- **Extend the container entrypoint** to read `AZURE_DEVOPS_EXT_PAT` and
  the host list and write `git config --system url."https://oauth2:$TOKEN@<host>".insteadOf "https://<host>"`
  for each host. Azure Repos HTTPS auth accepts any non-empty username
  paired with a PAT, so the `oauth2:` prefix the existing helper hard-
  codes works unchanged. The `--system` write goes to `/etc/gitconfig`
  which is discarded on `docker run --rm` exit, matching the established
  ephemerality story for `--gh`/`--glab`.
- **Add the `ado` tag to `CLAUDE_DOCKER_FLAGS`** so the statusline
  surfaces it like the other opt-ins.
- **Update README** to add the `--ado` row to the credential opt-in
  table, auth model table, and threat-model "Exposed" bullet; extend the
  "Private git module fetch" Scope paragraph.

Out of scope (deliberately):

- Mounting a host PAT file. Azure DevOps doesn't ship a CLI-tool config
  file at a stable cross-platform path with a parseable PAT field; PATs
  live in env vars or the OS keychain. Env-var forwarding is the only
  surface here.
- Host-side fallback to retrieve the PAT (analogue of `gh auth token` /
  `glab auth token`). The `az` CLI offers no equivalent — `az devops
  login` writes opaque session state, not a fetchable PAT.
- SSH-based git auth against Azure DevOps. Same SSH-agent threat-surface
  argument applies as for `--gh`/`--glab`.
- Self-hosted Azure DevOps Server URL parsing. Users who need it can set
  `CLAUDE_DOCKER_ADO_HOSTS` explicitly; no automatic enumeration.

## Capabilities

### New Capabilities

None. This change extends an existing capability.

### Modified Capabilities

- `external-cli-tools`: adds the `--ado` opt-in flag (env-var forwarding
  + git insteadOf injection for `dev.azure.com` or a user-supplied host
  list). The "credentials opt-in" invariant is preserved — the new
  behaviour only fires when the flag is set, and no Azure DevOps PAT
  reaches the container without it.

## Impact

- **Code**: `claude-docker/run.sh` (parse `--ado`, forward
  `AZURE_DEVOPS_EXT_PAT` + `CLAUDE_DOCKER_ADO_HOSTS`, tag statusline);
  `claude-docker/entrypoint.sh` (one extra `inject_insteadof` call).
- **Docs**: `claude-docker/README.md` (credential opt-in row, auth model
  row, threat-model bullet, scope note in Private git module fetch).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.** Existing flags and defaults unchanged;
  `--ado` is purely additive and gated.
- **Dependencies**: no new binaries. The existing entrypoint helper
  handles the new host group with no refactor (Azure DevOps accepts the
  same `oauth2:<tok>@<host>` shape gh/glab use).
