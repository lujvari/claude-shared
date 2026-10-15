## ADDED Requirements

### Requirement: Cloudflare credential opt-in

`run.sh` SHALL forward `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` into the container only when the user passes `--cloudflare`, each only when non-empty. `CLOUDFLARE_API_TOKEN` SHALL come from the host environment when set there; otherwise, when `CLAUDE_DOCKER_CLOUDFLARE_OP_REF` names an `op://` reference, `run.sh` SHALL resolve it with `op read` on the host. `CLOUDFLARE_ACCOUNT_ID` is not a secret and SHALL have no `op read` path. There SHALL be no built-in default reference, no bind mount, no in-container `wrangler login` state, and no git credential helper or `insteadOf` rewrite for this flag. When the flag is set, `run.sh` SHALL add `cloudflare` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and `CLOUDFLARE_API_TOKEN` is still empty, or the `op read` failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Host env vars are forwarded

- **GIVEN** `CLOUDFLARE_API_TOKEN=faketoken` and `CLOUDFLARE_ACCOUNT_ID=<account-id>` are exported on the host
- **WHEN** the user runs `claude-docker --cloudflare ~/repo`
- **THEN** both variables are set inside the container with the host values
- **AND** `CLAUDE_DOCKER_FLAGS` contains `cloudflare`

#### Scenario: Token is read from 1Password when unset on the host

- **GIVEN** `CLOUDFLARE_API_TOKEN` is not set on the host
- **AND** `CLAUDE_DOCKER_CLOUDFLARE_OP_REF=op://<vault>/<item>/<field>` names a readable item
- **WHEN** the user runs `claude-docker --cloudflare ~/repo`
- **THEN** `CLOUDFLARE_API_TOKEN` inside the container is non-empty

#### Scenario: No flag, no token

- **GIVEN** `CLOUDFLARE_API_TOKEN` is exported on the host
- **WHEN** the user runs `claude-docker ~/repo` without `--cloudflare`
- **THEN** neither `CLOUDFLARE_API_TOKEN` nor `CLOUDFLARE_ACCOUNT_ID` is set inside the container

#### Scenario: Account id alone does not satisfy the flag

- **GIVEN** only `CLOUDFLARE_ACCOUNT_ID` is set on the host and `CLAUDE_DOCKER_CLOUDFLARE_OP_REF` is unset
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --cloudflare ~/repo`
- **THEN** `run.sh` names `--cloudflare` on stderr and exits non-zero without starting a container

#### Scenario: Help lists the flag and the wrangler pin

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--cloudflare`, `CLAUDE_DOCKER_CLOUDFLARE_OP_REF`, and `npx wrangler@3`
