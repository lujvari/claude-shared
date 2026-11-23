## ADDED Requirements

### Requirement: Service boxes mount the architecture model

The `cd-mep`, `cd-brain` and `cd-board` launchers SHALL mount `laslo/architecture` at `/workspaces/architecture`, after their own project, read-write unless `--ro` is given. The box's working directory, agent-bus mailbox key and uv venv key SHALL stay those of the project. When `laslo/architecture` is missing from the dev root, the launcher SHALL stop with the `workspace not found` error before starting a test database or a box.

#### Scenario: The model is visible and writable

- **GIVEN** `laslo/architecture` exists under the dev root
- **WHEN** the owner runs `cd-mep`
- **THEN** `/workspaces/architecture` in the box holds the model, and a file written there appears in the host checkout

#### Scenario: Working directory and mailbox are unchanged

- **GIVEN** `laslo/architecture` exists under the dev root
- **WHEN** the owner runs `cd-brain`
- **THEN** the session starts in `/workspaces/brain` and `AGENT_BUS_SELF` is `laslo.brain`

#### Scenario: Test database still comes up for the project

- **GIVEN** `laslo/architecture` exists under the dev root
- **WHEN** the owner runs `cd-mep`
- **THEN** the test database is brought up from myEntryPoint's `compose.test.yml`, as before

#### Scenario: Missing model checkout

- **GIVEN** `laslo/architecture` does not exist under the dev root
- **WHEN** the owner runs `cd-brain`
- **THEN** the launcher prints `workspace not found` with the path, and starts neither the test database nor a box

#### Scenario: Arguments still pass through

- **GIVEN** `laslo/architecture` exists under the dev root
- **WHEN** the owner runs `cd-board -- --continue`
- **THEN** `--continue` reaches claude and both workspaces are mounted

#### Scenario: Read-only launch

- **GIVEN** `laslo/architecture` exists under the dev root
- **WHEN** the owner runs `cd-board --ro`
- **THEN** both workspaces are mounted read-only
