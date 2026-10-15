## ADDED Requirements

### Requirement: RingRecipe live-E2E account opt-in

`run.sh` SHALL forward `E2E_EMAIL`, `E2E_PASSWORD`, `E2E2_EMAIL`, `E2E2_PASSWORD`, `SUPABASE_URL` and `SUPABASE_ANON_KEY` into the container only when the user passes `--rr-e2e`, each only when non-empty. Each value SHALL come from the host environment when set there. For each of the four account variables still empty, `run.sh` SHALL read the `username` or `password` field of the 1Password item named by `CLAUDE_DOCKER_RR_E2E_OP_ITEM` (first account) or `CLAUDE_DOCKER_RR_E2E2_OP_ITEM` (second account). These SHALL default to `op://claude-docker/RingRecipe e2e account` and `op://claude-docker/RingRecipe e2e2 account` when unset, and an explicitly empty value SHALL disable that account's 1Password path. `SUPABASE_URL` and `SUPABASE_ANON_KEY` SHALL have no `op read` path. When the flag is set, `run.sh` SHALL add `rr-e2e` to `CLAUDE_DOCKER_FLAGS`. When the flag is set and both `E2E_PASSWORD` and `E2E2_PASSWORD` are still empty, or any of its `op read` calls failed, `run.sh` SHALL abort before `docker run` unless `CLAUDE_DOCKER_OP_OPTIONAL=1` is set.

#### Scenario: Default items supply both accounts

- **GIVEN** none of the four account variables and neither `*_OP_ITEM` variable is set on the host
- **AND** the host `op` can read both default items
- **WHEN** the user runs `claude-docker --rr-e2e ~/ringrecipe`
- **THEN** `E2E_EMAIL`, `E2E_PASSWORD`, `E2E2_EMAIL` and `E2E2_PASSWORD` are non-empty inside the container
- **AND** `CLAUDE_DOCKER_FLAGS` contains `rr-e2e`

#### Scenario: Non-secret connection pair comes from the env file only

- **GIVEN** `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set in the claude-docker env file
- **WHEN** the user runs `claude-docker --rr-e2e ~/ringrecipe`
- **THEN** both are set inside the container
- **AND** `run.sh` issues no `op read` for either

#### Scenario: One account switched off

- **GIVEN** `CLAUDE_DOCKER_RR_E2E2_OP_ITEM=""` and no `E2E2_*` variables on the host
- **AND** the first account resolves
- **WHEN** the user runs `claude-docker --rr-e2e ~/ringrecipe`
- **THEN** the container starts with `E2E_EMAIL` and `E2E_PASSWORD` set and `E2E2_PASSWORD` unset

#### Scenario: Both accounts switched off aborts the launch

- **GIVEN** both `*_OP_ITEM` variables are `""` and neither password is set on the host
- **AND** `CLAUDE_DOCKER_OP_OPTIONAL` is not `1`
- **WHEN** the user runs `claude-docker --rr-e2e ~/ringrecipe`
- **THEN** `run.sh` names `--rr-e2e` on stderr and exits non-zero without starting a container

#### Scenario: No flag, no accounts

- **GIVEN** the six variables are exported on the host
- **WHEN** the user runs `claude-docker ~/ringrecipe` without `--rr-e2e`
- **THEN** none of them is set inside the container

#### Scenario: Help lists the flag and its default items

- **WHEN** the user runs `claude-docker --help`
- **THEN** the output includes `--rr-e2e`, `CLAUDE_DOCKER_RR_E2E_OP_ITEM` and `CLAUDE_DOCKER_RR_E2E2_OP_ITEM`
