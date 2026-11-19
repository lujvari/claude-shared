## ADDED Requirements

### Requirement: Named Azure DevOps profiles

A named profile is selected by `CLAUDE_DOCKER_ADO_PROFILE` in the launching environment. `run.sh` SHALL ignore that key in the claude-docker env file, so the env file can never turn a default box into a profile box. The profile name SHALL match `[a-z0-9]+`; any other value SHALL abort the launch before `docker run` with an error naming the variable. `<NAME>` below is the profile name upper-cased.

When a profile is set and `--ado` is given, `run.sh` SHALL:

- take the PAT only from `op read "$CLAUDE_DOCKER_ADO_<NAME>_OP_REF"`, and forward it to the container as `AZURE_DEVOPS_EXT_PAT`;
- take the org list only from `CLAUDE_DOCKER_ADO_<NAME>_ORGS`. The list is comma-separated, and each org matches `[A-Za-z0-9-]+`. The orgs are kept as spelled, because git matches the URL path case-sensitively;
- abort before `docker run` when the op-ref is unset, the read fails or returns nothing, or the org list is empty or invalid. `CLAUDE_DOCKER_OP_OPTIONAL=1` SHALL NOT turn any of these into a warning;
- show the opt-in as `ado:<name>` in `CLAUDE_DOCKER_FLAGS`.

When a profile is set, `run.sh` SHALL NOT forward a host `AZURE_DEVOPS_EXT_PAT`. It SHALL NOT use `CLAUDE_DOCKER_ADO_OP_REF`, or a host-set `CLAUDE_DOCKER_ADO_ORG` or `CLAUDE_DOCKER_ADO_HOSTS`. The profile's org list takes the place of `CLAUDE_DOCKER_ADO_ORG` for the token probe.

When a profile is set and `--ado-admin` is given, with or without `--ado`, `run.sh` SHALL abort before `docker run` without reading any admin PAT.

In a profile box, the git credential helper SHALL answer with the PAT only for `https://dev.azure.com/<org>` and paths below it, for each org in the profile. It SHALL NOT answer for any other ADO URL. This SHALL hold on images built before this change too, back to the move to the credential helper, so a stale image never widens the scope. The token probe SHALL make one request per org in the profile, and warn for each org that rejects the PAT.

When `CLAUDE_DOCKER_ADO_PROFILE` is unset or empty, `--ado` SHALL behave as before this change. With neither `--ado` nor `--ado-admin`, the profile variables SHALL have no effect.

This requirement takes precedence, for profile boxes, over the `--ado` forwarding in "Credentials opt-in" and the one-request-per-flag rule in "Launch-time token probe".

#### Scenario: Profile PAT reaches the box

- **GIVEN** `CLAUDE_DOCKER_ADO_PROFILE=apg`, `CLAUDE_DOCKER_ADO_APG_OP_REF` points at a readable item and `CLAUDE_DOCKER_ADO_APG_ORGS=aamnld`
- **WHEN** the user runs `claude-docker --ado ~/repo`
- **THEN** `AZURE_DEVOPS_EXT_PAT` in the container equals the item's value
- **AND** `CLAUDE_DOCKER_FLAGS` contains `ado:apg` and not a bare `ado`

#### Scenario: Host PAT does not leak into a profile box

- **GIVEN** the host exports `AZURE_DEVOPS_EXT_PAT=<sbp token>` and the `apg` profile is set up as above
- **WHEN** the user runs `claude-docker --ado ~/repo`
- **THEN** `AZURE_DEVOPS_EXT_PAT` in the container equals the `apg` item's value, not the SBP token

#### Scenario: Env file cannot select a profile

- **GIVEN** the env file contains `CLAUDE_DOCKER_ADO_PROFILE=apg` and the launching environment does not set it
- **WHEN** `cd-ct` launches
- **THEN** the box is a default ADO box (tag `ado`, or `ado:<label>` from the launcher; default PAT)

#### Scenario: Missing or unreadable profile op-ref aborts

- **GIVEN** `CLAUDE_DOCKER_ADO_PROFILE=apg`, and `CLAUDE_DOCKER_ADO_APG_OP_REF` either unset or pointing at an item that does not exist, while `CLAUDE_DOCKER_ADO_OP_REF` points at the SBP item
- **WHEN** the user runs `claude-docker --ado ~/repo`, with or without `CLAUDE_DOCKER_OP_OPTIONAL=1`
- **THEN** `run.sh` exits non-zero before `docker run`, naming `CLAUDE_DOCKER_ADO_APG_OP_REF`

#### Scenario: Empty or invalid org list aborts

- **GIVEN** the `apg` op-ref resolves and `CLAUDE_DOCKER_ADO_APG_ORGS` is unset, empty, `a/b` or `a,,b`
- **WHEN** the user runs `claude-docker --ado ~/repo`
- **THEN** `run.sh` exits non-zero before `docker run`, naming `CLAUDE_DOCKER_ADO_APG_ORGS`

#### Scenario: Invalid profile name aborts

- **GIVEN** `CLAUDE_DOCKER_ADO_PROFILE` is `apg;x` or `APG`
- **WHEN** the user runs `claude-docker --ado ~/repo`
- **THEN** `run.sh` exits non-zero before `docker run`, naming `CLAUDE_DOCKER_ADO_PROFILE`

#### Scenario: Admin PAT refused under a profile

- **GIVEN** `CLAUDE_DOCKER_ADO_PROFILE=apg`
- **WHEN** the user runs `claude-docker --ado-admin ~/repo` or `claude-docker --ado --ado-admin ~/repo`
- **THEN** `run.sh` exits non-zero before `docker run`, and no admin PAT is read

#### Scenario: Profile without an ADO flag is inert

- **GIVEN** the `apg` profile variables are set
- **WHEN** the user runs `claude-docker ~/repo`
- **THEN** no ADO PAT is read or forwarded, and `CLAUDE_DOCKER_FLAGS` has no `ado` tag

#### Scenario: git offers the PAT to profile orgs only

- **GIVEN** a container launched with the `apg` profile and orgs `aamnld`, with `CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com` set on the host, on either the current image or one built before this change that already uses the credential helper
- **WHEN** `git credential fill` runs for `https://dev.azure.com/aamnld/ccoe/_git/platform-iam`, `https://aamnld@dev.azure.com/aamnld/ccoe/_git/platform-iam`, `https://dev.azure.com/sbp-controltower/x/_git/y` and `https://dev.azure.com/aamnldx/x/_git/y`
- **THEN** the first two return the profile PAT as the password
- **AND** the last two return no password from the helper

#### Scenario: Probe covers every profile org

- **GIVEN** `CLAUDE_DOCKER_ADO_APG_ORGS=orga,orgb`, where `orga` accepts the PAT and `orgb` answers 401
- **WHEN** the token probe runs at launch
- **THEN** it makes two requests, prints one warning naming `--ado@orgb`, and nothing about `orga`

#### Scenario: No profile keeps today's behaviour

- **GIVEN** `CLAUDE_DOCKER_ADO_PROFILE` unset, and the env file sets `CLAUDE_DOCKER_ADO_OP_REF` and `CLAUDE_DOCKER_ADO_ORG=sbp-controltower`
- **WHEN** `cd-ct` launches
- **THEN** the PAT source, the git helper scope (all of `dev.azure.com`), the probe and the `ado` tag are as before this change

### Requirement: Display label for a default Azure DevOps box

`CLAUDE_DOCKER_ADO_LABEL`, read from the launching environment only (`run.sh` SHALL ignore it in the env file), SHALL change the tag of a default `--ado` box in `CLAUDE_DOCKER_FLAGS` to `ado:<label>`. It SHALL change nothing else: not the PAT source, git helper scope, token probe or masking. A profile box SHALL keep `ado:<profile>` and ignore the label.

#### Scenario: Control-tower box shows its label

- **GIVEN** `cd-ct` exports `CLAUDE_DOCKER_ADO_LABEL=ct` and no profile
- **WHEN** it launches with `--ado`
- **THEN** `CLAUDE_DOCKER_FLAGS` contains `ado:ct`, and the box is otherwise a default ADO box

### Requirement: Persisted Azure DevOps CLI state is visible only to default ADO boxes

`az devops login` and `az devops configure` keep a PAT and default org/project under `~/.azure/azuredevops` and `~/.azure-devops`, in the home volume every box shares. When the home volume is mounted, a box SHALL see that persisted state only when it runs `--ado` without a named profile. Every other box SHALL get empty, writable, box-owned directories at both paths for that run, and nothing written there SHALL persist. This includes boxes with no ADO flag and profile boxes.

#### Scenario: Client box cannot read the SBP az devops state

- **GIVEN** a default `--ado` box has written `~/.azure/azuredevops/personalAccessTokens` and `config`
- **WHEN** `cd-apg` (profile `apg`) or a box without `--ado` starts
- **THEN** `~/.azure/azuredevops` and `~/.azure-devops` are empty in that box

#### Scenario: Default ADO box keeps its az devops defaults

- **GIVEN** the persisted `~/.azure/azuredevops/config` sets a default org and project
- **WHEN** `cd-ct` starts
- **THEN** `az devops configure --list` shows those defaults

#### Scenario: Profile box writes do not persist

- **GIVEN** a profile box runs `az devops configure --defaults organization=https://dev.azure.com/aamnld`
- **WHEN** the next `cd-ct` box starts
- **THEN** its `az devops configure --list` still shows the SBP defaults
