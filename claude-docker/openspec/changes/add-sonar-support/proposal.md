> Retroactive record: implemented in 47cd75f on 2026-09-23, written 2026-10-15 to close spec drift.

Note: 47cd75f is titled "abort the launch when a flag's credential fails to
resolve" and its message does not mention `--sonar`; the flag landed inside
it. 3d6a3a8 (2026-10-07) later added `--sonar` to `launchers/cd-ct`.

## Why

In-container scripts need to read SonarCloud quality-gate status and measures
over the Web API, which authenticates with a bearer token from `SONAR_TOKEN`.
The container had no way to receive it. `sonar-scanner` takes its token from
the environment or a CLI argument and writes no login file, so there is no
on-disk second source; the env var is the whole auth path.

The token type matters: a project analysis token is bound to one project and
answers `404 Project doesn't exist` for any other, which SonarCloud also
returns to an unauthorized caller for a private project. A user token is
required, and failures read as "project missing" rather than as auth errors.

## What Changes

- **Add `--sonar` opt-in flag** to `run.sh` that forwards `SONAR_TOKEN` and
  the non-secret `SONAR_HOST_URL` from the host when set. No flag → neither
  reaches the container.
- **1Password fallback for the token only** via `CLAUDE_DOCKER_SONAR_OP_REF`
  (`op://<vault>/<item>/<field>`). No built-in default ref.
  `SONAR_HOST_URL` has no op path.
- **Statusline tag** `sonar`.
- **Fail closed** from the start (it shipped in the commit that introduced
  the gate): a failed read, or the flag ending with no `SONAR_TOKEN`, aborts
  before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1`.
- **No mount, no CLI fallback, no git credential injection.**
- **README**: opt-in row, auth-model row, statusline tag, and a "SonarCloud"
  section on minting a user token and the 404 ambiguity.

Out of scope (deliberately):

- Narrower-than-user token scopes, which SonarCloud does not offer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: adds a SonarCloud credential opt-in.

## Impact

- **Code**: `claude-docker/run.sh`; `claude-docker/launchers/cd-ct` (3d6a3a8).
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.**
