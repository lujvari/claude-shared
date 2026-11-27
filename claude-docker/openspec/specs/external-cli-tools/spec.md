# external-cli-tools

## Purpose

Provide `gh`, `glab`, and AWS CLI v2 inside the container with minimal re-auth friction, using host credential passthrough where the tool's macOS storage is file-based and in-container persistence otherwise.
## Requirements
### Requirement: gh, glab, aws v2 installed

The container image SHALL ship with `gh`, `glab`, and `aws` (v2) on the default PATH, built arch-aware for both `amd64` and `arm64`.

#### Scenario: CLIs present

- **WHEN** the container launches
- **THEN** `gh --version`, `glab --version`, and `aws --version` all succeed

#### Scenario: Builds on Apple Silicon

- **WHEN** `docker build -t claude-code:local ~/claude-docker` runs on arm64
- **THEN** the build succeeds and no CLI fails with exec-format error

### Requirement: Credentials opt-in

Host credentials (files or env vars) SHALL NOT reach the container unless the user explicitly opts in per-run. `run.sh` defaults to no credential mounts and no token env forwarding. Opt-ins are granted via dedicated flags:

> **Superseded in part (2026-09-23, `add-credential-fail-closed`):** every clause below saying `run.sh` continues silently when a token can't be resolved no longer holds. A credential flag that ends up without its credential now aborts the launch unless `CLAUDE_DOCKER_OP_OPTIONAL=1`. Silence about absent mounts is unaffected.

- `--aws`: mount `~/.aws/config` at `/home/claude/.aws/config:ro` and, when present, `~/.aws/sso/` at `/home/claude/.aws/sso:ro`; forward `AWS_PROFILE`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` when set on the host.
- `--gh`: forward `GH_TOKEN` or `GITHUB_TOKEN` when set on the host. If neither
  is set, `run.sh` SHALL attempt to retrieve the active token by running
  `gh auth token` on the host and forward the result as `GH_TOKEN`. If `gh` is
  not on the host PATH or the command fails, `run.sh` SHALL continue silently
  without a token.
- `--glab`: mount no glab config. `/home/claude/.config/glab-cli` is always tmpfs-masked. Forward `GITLAB_TOKEN`, taken from the host env var or `op read "$CLAUDE_DOCKER_GITLAB_OP_REF"`. Forward `GITLAB_HOST` when it is set on the host. Forward `CLAUDE_DOCKER_GITLAB_HOSTS` when it is set on the host. `run.sh` SHALL NOT derive any GitLab host from the host glab config. When `CLAUDE_DOCKER_GITLAB_HOSTS` is unset, the entrypoint installs the GitLab credential helper for `gitlab.com` only.

All credential bind-mounts SHALL be read-only so a compromised container cannot rewrite host config or tokens. `~/.aws/credentials` and `~/.aws/cli/cache/` SHALL NEVER be mounted, even under `--aws`.

#### Scenario: No flags means no credentials

- **GIVEN** host has `~/.aws/config`, `~/.config/glab-cli/config.yml`, and `GH_TOKEN=ghp_x` exported
- **AND** a prior container run completed `gh auth login` (state persisted in `claude-code-root`)
- **WHEN** user runs `claude-docker ~/repo`
- **THEN** `/home/claude/.aws/` does not exist inside the container
- **AND** `/home/claude/.config/glab-cli/` is empty inside the container
- **AND** `echo $GH_TOKEN` inside the container is empty
- **AND** `gh auth status` inside the container reports "not logged in"

#### Scenario: --aws grants scoped AWS access

- **GIVEN** the host has completed `aws sso login --profile X` and exports `AWS_PROFILE=X`
- **WHEN** user runs `claude-docker --aws ~/repo`
- **THEN** `aws sts get-caller-identity` inside the container returns the host's identity
- **AND** `~/.aws/credentials` is not present inside the container
- **AND** writes to `/home/claude/.aws/` from inside the container fail with EROFS

#### Scenario: --glab host list comes only from the environment

- **GIVEN** the host `~/.config/glab-cli/config.yml` lists `gitlab.com` and `sbp.gitlab.schubergphilis.com`
- **AND** `CLAUDE_DOCKER_GITLAB_HOSTS=sbp.gitlab.schubergphilis.com` is exported
- **WHEN** the user runs `claude-docker --glab ~/repo`
- **THEN** the container's git credential helpers cover `https://sbp.gitlab.schubergphilis.com` only

#### Scenario: --glab forwards GITLAB_HOST

- **GIVEN** `GITLAB_HOST=sbp.gitlab.schubergphilis.com` is exported on the host
- **WHEN** the user runs `claude-docker --glab ~/repo`
- **THEN** `echo $GITLAB_HOST` inside the container prints `sbp.gitlab.schubergphilis.com`
- **AND** `glab mr list` in an sbp.gitlab repo resolves that host without further setup

#### Scenario: SBP launchers pin the GitLab host

- **WHEN** `cd-cis`, `cd-inat`, `cd-asr`, `cd-ta` or `cd-apg` starts a box
- **THEN** the launcher has exported `GITLAB_HOST` and `CLAUDE_DOCKER_GITLAB_HOSTS`, both set to `sbp.gitlab.schubergphilis.com`, before `exec`ing `run.sh`

#### Scenario: --gh forwards host env token

- **GIVEN** `GH_TOKEN=ghp_x` is exported in the host shell
- **WHEN** user runs `claude-docker --gh ~/repo`
- **THEN** `echo $GH_TOKEN` inside the container prints `ghp_x`

#### Scenario: --gh falls back to gh auth token

- **GIVEN** neither `GH_TOKEN` nor `GITHUB_TOKEN` is set in the host shell
- **AND** the host has `gh` on PATH and the user is authenticated (`gh auth status` succeeds)
- **WHEN** user runs `claude-docker --gh ~/repo`
- **THEN** `echo $GH_TOKEN` inside the container prints the token returned by `gh auth token`

#### Scenario: --gh is silent when gh is unavailable

- **GIVEN** neither `GH_TOKEN` nor `GITHUB_TOKEN` is set in the host shell
- **AND** `gh` is not on the host PATH (or `gh auth token` exits non-zero)
- **WHEN** user runs `claude-docker --gh ~/repo`
- **THEN** the container starts without a `GH_TOKEN` env var and no error is printed

### Requirement: In-container gh login persists only under --gh

Because macOS `gh` uses the Keychain (no host file to mount), the container SHALL support a fresh `gh auth login` whose resulting `~/.config/gh/` persists across runs via the existing `claude-code-root` volume. Access to that persisted state SHALL be gated on `--gh` being passed in the current run: when `--gh` is not set, `/home/claude/.config/gh/` inside the container MUST appear empty (achieved by overlaying a tmpfs mask) so a prior login cannot grant credentials to a session the user didn't opt in to. The same masking rule SHALL apply to `/home/claude/.config/glab-cli/` when `--glab` is not set.

#### Scenario: gh login survives container exit under --gh

- **GIVEN** user completes `gh auth login` inside a container launched with `--gh`
- **WHEN** they exit and relaunch with `--gh`
- **THEN** `gh auth status` reports "logged in" without re-prompting

#### Scenario: prior gh login is hidden without --gh

- **GIVEN** a prior container run completed `gh auth login` (state persisted in `claude-code-root`)
- **WHEN** user runs `claude-docker ~/repo` without `--gh`
- **THEN** `gh auth status` inside the container reports "not logged in"
- **AND** `/home/claude/.config/gh/` inside the container is empty

#### Scenario: prior glab login is hidden without --glab

- **GIVEN** a prior container run completed `glab auth login` (state persisted in `claude-code-root`)
- **WHEN** user runs `claude-docker ~/repo` without `--glab`
- **THEN** `glab auth status` inside the container reports no authenticated host
- **AND** `/home/claude/.config/glab-cli/` inside the container is empty

### Requirement: CIS credential opt-in

`run.sh` SHALL forward `CIS_API_KEY` into the container only when the user passes `--cis`, and only when non-empty. It SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_CIS_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. There SHALL be no built-in default reference and no bind mount. When the flag is set, `run.sh` SHALL add `cis` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `CIS_API_KEY` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Key is read from 1Password when unset on the host

- **GIVEN** `CIS_API_KEY` is not set on the host
- **AND** `CLAUDE_DOCKER_CIS_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --cis ~/repo`
- **THEN** `CIS_API_KEY` inside the container is non-empty
- **AND** `CLAUDE_DOCKER_FLAGS` contains `cis`

#### Scenario: No flag, no key

- **GIVEN** `CIS_API_KEY` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--cis`
- **THEN** `CIS_API_KEY` is not set inside the container

#### Scenario: Unresolved key aborts

- **GIVEN** `CIS_API_KEY` and `CLAUDE_DOCKER_CIS_OP_REF` are unset on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --cis ~/repo`
- **THEN** `run.sh` names `--cis` on stderr and exits non-zero without starting a container

### Requirement: npm feed credential derived from the ADO PAT

When the user passes `--npm-feed`, `run.sh` SHALL set `NPM_FEED_PASSWORD` in the container to the base64 encoding, without line breaks, of the `AZURE_DEVOPS_EXT_PAT` the box receives. `--npm-feed` without `--ado` SHALL abort before `docker run` with an error naming both flags. Without `--npm-feed`, `NPM_FEED_PASSWORD` SHALL NOT be set in the container, even when the host has it. When the flag is set, `run.sh` SHALL add `npm-feed` to `CLAUDE_DOCKER_FLAGS`.

#### Scenario: Feed credential reaches a CT box

- **GIVEN** `~/.npmrc` sets the feed's `_password` to `${NPM_FEED_PASSWORD}`
- **AND** the `--ado` PAT has Packaging (Read) on the feed
- **WHEN** the user runs `cd-ct`
- **THEN** `npm view` of a package on the feed succeeds inside the box
- **AND** `CLAUDE_DOCKER_FLAGS` contains `npm-feed`

#### Scenario: No flag, no feed credential

- **WHEN** the user runs `claude-docker --ado ~/repo` without `--npm-feed`
- **THEN** `NPM_FEED_PASSWORD` is not set inside the container
- **AND** `npm view left-pad version` still succeeds

#### Scenario: Flag without --ado aborts

- **WHEN** the user runs `claude-docker --npm-feed ~/repo`
- **THEN** `run.sh` names `--npm-feed` and `--ado` on stderr and exits non-zero without starting a container

### Requirement: Credential flags fail closed

When the user passes a credential flag, `run.sh` SHALL NOT start a container that lacks the credential that flag asked for. It SHALL abort before `docker run` with a non-zero exit and a stderr message naming the flag or the op-ref when: `op` is not on PATH while a flag needs it; the `op whoami` preflight fails; any `op read` fails; or, after all credential sources, none of the flag's env vars is set. The end-state check SHALL cover `--gh`, `--glab`, `--ado`, `--ado-admin`, `--jira`, `--supabase`, `--cloudflare`, `--openrouter`, `--sonar`, `--mepdb`, `--rr-e2e` and `--hetzner-infra`, and SHALL NOT cover `--aws`, `--tfe` or `--tofu`, whose credentials may arrive by mount. When `CLAUDE_DOCKER_OP_OPTIONAL=1` is set, each of these aborts SHALL instead print a warning and the launch SHALL continue. This requirement takes precedence over any earlier clause saying `run.sh` continues silently when a token cannot be resolved.

#### Scenario: Failed read aborts the launch

- **GIVEN** `POSTGRES_TEST_URL` is unset on the host and `op read` of the `--mepdb` ref fails
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** stderr names the ref that was not delivered
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: --gh with no token source aborts

- **GIVEN** neither `GH_TOKEN` nor `GITHUB_TOKEN` is set, `CLAUDE_DOCKER_GITHUB_OP_REF` is unset, and `gh auth token` yields nothing
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --gh ~/repo`
- **THEN** stderr says `--gh` injected nothing
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: Expired token is reported once

- **GIVEN** no host `GH_TOKEN`/`GITHUB_TOKEN`/`POSTGRES_TEST_URL`, and `CLAUDE_DOCKER_GITHUB_OP_REF` is set
- **AND** `op whoami` returns (403) Forbidden
- **WHEN** the user runs `claude-docker --gh --mepdb ~/repo`
- **THEN** stderr carries one preflight failure naming both flags, and no per-ref read errors
- **AND** `run.sh` exits non-zero without starting a container

#### Scenario: Escape hatch launches without the credential

- **GIVEN** the `--mepdb` read fails
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL=1` is set
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** stderr warns that the container will be missing the credential
- **AND** the container starts without `POSTGRES_TEST_URL`

#### Scenario: Mount-based flags are not asserted

- **GIVEN** the host has `~/.aws/config` and an SSO cache but no `AWS_ACCESS_KEY_ID` and no `CLAUDE_DOCKER_AWS_OP_REF`
- **WHEN** the user runs `claude-docker --aws ~/repo`
- **THEN** the container starts

### Requirement: myEntryPoint test database opt-in

`run.sh` SHALL forward `POSTGRES_TEST_URL` into the container only when the user passes `--mepdb`. The value SHALL come from the host environment when set there; otherwise `run.sh` SHALL resolve `CLAUDE_DOCKER_MEPDB_OP_REF` with `op read` on the host. `CLAUDE_DOCKER_MEPDB_OP_REF` SHALL default to `op://claude-docker/brain-test-postgres/dsn` when unset, and an explicitly empty value SHALL disable the 1Password path. There SHALL be no bind mount and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `mepdb` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `POSTGRES_TEST_URL` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Default reference is used with no configuration

- **GIVEN** `POSTGRES_TEST_URL` and `CLAUDE_DOCKER_MEPDB_OP_REF` are both unset on the host
- **AND** the host `op` can read `op://claude-docker/brain-test-postgres/dsn`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `POSTGRES_TEST_URL` inside the container is non-empty
- **AND** `CLAUDE_DOCKER_FLAGS` contains `mepdb`

#### Scenario: Host env var wins over the default reference

- **GIVEN** `POSTGRES_TEST_URL=<dsn>` is exported on the host
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `POSTGRES_TEST_URL` inside the container equals the host value
- **AND** no `op read` is issued for this flag

#### Scenario: Empty reference switches the 1Password path off

- **GIVEN** `POSTGRES_TEST_URL` is unset and `CLAUDE_DOCKER_MEPDB_OP_REF=""` on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --mepdb ~/repo`
- **THEN** `run.sh` issues no `op read` for this flag, names `--mepdb` on stderr, and exits non-zero without starting a container

#### Scenario: No flag, no DSN

- **GIVEN** `POSTGRES_TEST_URL` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--mepdb`
- **THEN** `POSTGRES_TEST_URL` is not set inside the container

#### Scenario: Help lists the flag and its default

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--mepdb` and `op://claude-docker/brain-test-postgres/dsn`

### Requirement: Supabase credential opt-in

`run.sh` SHALL forward `SUPABASE_ACCESS_TOKEN` into the container only when the user passes `--supabase`. The value SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_SUPABASE_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host and forward the result. There SHALL be no built-in default reference, no bind mount, and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `supabase` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and, after both sources, `SUPABASE_ACCESS_TOKEN` is empty or the `op read` failed, `run.sh` SHALL abort before `docker run` with a non-zero exit unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Host env var is forwarded

- **GIVEN** `SUPABASE_ACCESS_TOKEN=faketoken` is exported on the host
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `echo $SUPABASE_ACCESS_TOKEN` inside the container prints `faketoken`
- **AND** `CLAUDE_DOCKER_FLAGS` contains `supabase`

#### Scenario: Token is read from 1Password when unset on the host

- **GIVEN** `SUPABASE_ACCESS_TOKEN` is not set on the host
- **AND** `CLAUDE_DOCKER_SUPABASE_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `SUPABASE_ACCESS_TOKEN` inside the container is non-empty

#### Scenario: No flag, no token

- **GIVEN** `SUPABASE_ACCESS_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--supabase`
- **THEN** `SUPABASE_ACCESS_TOKEN` is not set inside the container

#### Scenario: Flag that resolves to nothing aborts the launch

- **GIVEN** `SUPABASE_ACCESS_TOKEN` and `CLAUDE_DOCKER_SUPABASE_OP_REF` are both unset on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --supabase ~/repo`
- **THEN** `run.sh` names `--supabase` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--supabase` and `CLAUDE_DOCKER_SUPABASE_OP_REF`

### Requirement: Elevated Azure DevOps PAT opt-in

`run.sh` SHALL forward `AZURE_DEVOPS_ADMIN_PAT` into the container only when the user passes `--ado-admin`. The value SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_ADO_ADMIN_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. There SHALL be no built-in default reference and no bind mount. `AZURE_DEVOPS_ADMIN_PAT` SHALL be forwarded alongside, never instead of, `--ado`'s `AZURE_DEVOPS_EXT_PAT`, and SHALL NOT be wired into the git credential helper, any `insteadOf` rewrite, or `az devops` configuration. When the flag is set, `run.sh` SHALL add `ado-admin` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `AZURE_DEVOPS_ADMIN_PAT` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Both PATs are forwarded side by side

- **GIVEN** `AZURE_DEVOPS_EXT_PAT=everyday` and `AZURE_DEVOPS_ADMIN_PAT=elevated` are exported on the host
- **WHEN** the user runs `claude-docker --ado --ado-admin ~/repo`
- **THEN** both variables are set inside the container with the host values
- **AND** the git credential helper for Azure DevOps answers with `AZURE_DEVOPS_EXT_PAT`, not `AZURE_DEVOPS_ADMIN_PAT`
- **AND** `CLAUDE_DOCKER_FLAGS` contains both `ado` and `ado-admin`

#### Scenario: Admin PAT is read from 1Password when unset on the host

- **GIVEN** `AZURE_DEVOPS_ADMIN_PAT` is not set on the host
- **AND** `CLAUDE_DOCKER_ADO_ADMIN_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --ado-admin ~/repo`
- **THEN** `AZURE_DEVOPS_ADMIN_PAT` inside the container is non-empty

#### Scenario: --ado alone does not carry the admin PAT

- **GIVEN** `AZURE_DEVOPS_ADMIN_PAT` is exported on the host
- **WHEN** the user runs `claude-docker --ado ~/repo` without `--ado-admin`
- **THEN** `AZURE_DEVOPS_ADMIN_PAT` is not set inside the container

#### Scenario: Flag that resolves to nothing aborts the launch

- **GIVEN** neither `AZURE_DEVOPS_ADMIN_PAT` nor `CLAUDE_DOCKER_ADO_ADMIN_OP_REF` is set on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --ado-admin ~/repo`
- **THEN** `run.sh` names `--ado-admin` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--ado-admin` and `CLAUDE_DOCKER_ADO_ADMIN_OP_REF`

### Requirement: Hetzner Cloud infrastructure opt-in

`run.sh` SHALL forward `HCLOUD_TOKEN` into the container only when the user passes `--hetzner-infra`. The value SHALL come from the host environment when set there; otherwise `run.sh` SHALL resolve `CLAUDE_DOCKER_HETZNER_OP_REF` with `op read` on the host. That variable SHALL default to `op://claude-docker-infra/hcloud-mep/token` when unset, and an explicitly empty value SHALL disable the 1Password path.

The read SHALL use the 1Password service-account token stored in the file named by `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` (default `~/.config/op/infra-service-account-token`), set only for that one read. It SHALL NOT be forwarded into the container or used for any other flag's read. When `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` is explicitly empty, the read SHALL use the everyday service account instead.

When the token file is missing, is empty, or does not start with `ops_`, `run.sh` SHALL report the file path (never its content) and treat the reference as a failed read. While a token file is in use, a failed everyday `op whoami` preflight SHALL NOT block a launch whose only 1Password read is this one.

There SHALL be no bind mount and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `hetzner-infra` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `HCLOUD_TOKEN` is still empty, or the read failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Token is read with the infra service account

- **GIVEN** `HCLOUD_TOKEN` is not set on the host
- **AND** the default token file holds a service-account token that can read the default reference
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo`
- **THEN** `HCLOUD_TOKEN` inside the container is non-empty
- **AND** `OP_SERVICE_ACCOUNT_TOKEN` is not set inside the container
- **AND** `CLAUDE_DOCKER_FLAGS` contains `hetzner-infra`

#### Scenario: Other flags keep the everyday account

- **GIVEN** the infra token file is valid
- **WHEN** the user runs `claude-docker --mepdb --hetzner-infra ~/repo`
- **THEN** the `--mepdb` reference is read with the everyday service account
- **AND** only the `--hetzner-infra` reference is read with the infra service account

#### Scenario: Missing or malformed token file aborts the launch

- **GIVEN** `HCLOUD_TOKEN` is not set on the host
- **AND** the token file is missing, empty, or does not start with `ops_`
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo`
- **THEN** `run.sh` names the token file path and the reference on stderr without printing the file's content
- **AND** exits non-zero without starting a container

#### Scenario: Dead everyday account does not block an infra-only launch

- **GIVEN** the everyday service-account token is revoked
- **AND** the infra token file is valid
- **WHEN** the user runs `claude-docker --hetzner-infra ~/repo` with no other 1Password-backed flag
- **THEN** the container starts with `HCLOUD_TOKEN` set

#### Scenario: No flag, no token

- **GIVEN** `HCLOUD_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--hetzner-infra`
- **THEN** `HCLOUD_TOKEN` is not set inside the container

#### Scenario: Help lists the flag and its defaults

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--hetzner-infra`, `op://claude-docker-infra/hcloud-mep/token` and `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE`

### Requirement: Brain MCP opt-in

`run.sh` SHALL accept `--brain`, and SHALL treat `CLAUDE_DOCKER_BRAIN=1` the
same way. Either one resolves `BRAIN_CF_ACCESS_CLIENT_ID` and
`BRAIN_CF_ACCESS_CLIENT_SECRET` and forwards them into the container. Values
SHALL come from the host environment, or else from
`CLAUDE_DOCKER_BRAIN_CF_ID_OP_REF` / `CLAUDE_DOCKER_BRAIN_CF_SECRET_OP_REF`,
which default to refs in the `claude-docker` vault. No secret value SHALL
appear in any committed file or in `~/.claude.json`.

#### Scenario: Launcher with default refs
- GIVEN the item `brain-cf-access` exists in vault `claude-docker`
- WHEN a `cd-*` launcher starts a box
- THEN both vars are set in the box
- AND `claude mcp list` shows `brain` connected
- AND a tools call (`list`) to `brain` succeeds

#### Scenario: Refs do not resolve
- GIVEN `--brain` and a ref that `op read` cannot resolve
- WHEN `run.sh` reaches the credential post-check
- THEN it exits non-zero before `docker run` and names `--brain`

#### Scenario: Plain run.sh without the flag
- WHEN `run.sh` runs without `--brain` and without `CLAUDE_DOCKER_BRAIN=1`
- THEN neither var reaches the container

### Requirement: Brain MCP entry seeded with placeholders

When both vars are non-empty, `entrypoint.sh` SHALL make sure a user-scope
HTTP MCP entry named `brain` exists for `https://brain.karansjet.dev/mcp`.
Its headers SHALL be the literal placeholders
`CF-Access-Client-Id: ${BRAIN_CF_ACCESS_CLIENT_ID}` and
`CF-Access-Client-Secret: ${BRAIN_CF_ACCESS_CLIENT_SECRET}`. The entrypoint
SHALL NOT remove an existing entry.

#### Scenario: Idempotent relaunch
- GIVEN the entry already exists
- WHEN a box starts again
- THEN the entry is left as it is, and the box still starts

#### Scenario: Endpoint rejects unauthenticated calls
- WHEN a request without the CF-Access headers is sent to the endpoint
- THEN it gets 403

