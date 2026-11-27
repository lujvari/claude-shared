## ADDED Requirements

### Requirement: Example seed allows reading the box's own config

`examples/settings.docker.json` SHALL allow, without a prompt, reading the box's installed skills (`~/.claude/skills`), inat user rules (`~/.inat/rules`) and user `CLAUDE.md`, with the Read tool and with read-only Bash commands. It SHALL add no other allow rule, and every existing deny rule SHALL still block, including for a path under an allowed directory.

#### Scenario: Reading an installed skill

- **GIVEN** a box started with the example seed, in default permission mode
- **WHEN** the session runs `head -2 ~/.claude/skills/agent-bus/SKILL.md`
- **THEN** it runs without a permission prompt

#### Scenario: Reading the user rules

- **GIVEN** the same box
- **WHEN** the session reads `~/.claude/CLAUDE.md` with the Read tool
- **THEN** it reads without a permission prompt

#### Scenario: A deny rule under an allowed path still blocks

- **GIVEN** the same box
- **WHEN** the session reads `~/.claude/skills/agent-bus/.env` with the Read tool
- **THEN** the read is denied

#### Scenario: Other commands still prompt

- **GIVEN** the same box
- **WHEN** the session runs `python3 -c "print(1)"`
- **THEN** Claude Code asks for permission first
