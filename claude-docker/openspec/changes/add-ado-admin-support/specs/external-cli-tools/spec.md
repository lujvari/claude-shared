## ADDED Requirements

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
