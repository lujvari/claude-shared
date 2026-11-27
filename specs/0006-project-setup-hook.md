# 0006 — per-project setup hook

**Status:** draft

## Purpose

Most cd-tools requests are "add tool X to the image for project Y" (0003: sqlcmd and sqlpackage for sbp.ct). Every one is an image change, a rebuild, and a tool every other box carries. A project should add its own tools: a script in its repo that the launcher runs before the box starts, with the result cached so later launches are instant. The image keeps only what every box needs.

The script is repo content, so it is treated as untrusted: it runs only after the owner approves that exact content, never with credentials, and it cannot read the box's home volume (OAuth tokens, gh login).

## Requirements

- REQ-1: When the first workspace contains `.claude-docker/setup.sh`, `run.sh` SHALL run it before starting the box, in a separate one-shot container from the same image: uid 1000, `--cap-drop ALL`, `no-new-privileges`, no credential env or file, no `claude-code-root`/`claude-code-home` volume, the workspace's `.claude-docker/` mounted read-only, and the project's tool volume mounted read-write at `/opt/project-tools`.
- REQ-2: `run.sh` SHALL run the script only when its sha256 matches one the owner approved for that box key. An unapproved or changed script SHALL be shown in full (first time) or as a diff against the last approved copy, and run only on an interactive `y`; with no TTY, or on any other answer, the setup step is skipped with one line saying why and how to approve. Approved copies live host-side under `~/.config/claude-docker/setup/<key>.sh`, outside every box mount.
- REQ-3: The setup step SHALL be skipped when the volume's stamp matches the script's sha256 and the image id; otherwise it runs and, only on exit 0, writes that stamp. `--setup-refresh` SHALL empty the volume and run it again.
- REQ-4: The tool volume SHALL be one named volume per box key (`claude-docker-tools-<key>`), mounted read-only in the box at `/opt/project-tools`, with `/opt/project-tools/bin` prepended to the box's `PATH` and `CLAUDE_DOCKER_PROJECT_TOOLS=/opt/project-tools` set.
- REQ-5: A failed setup (non-zero exit, timeout) SHALL print the exit status and the last lines of `/opt/project-tools/setup.log`, leave the stamp unwritten, and still start the box with whatever the volume already holds, so the script can be fixed from inside it.
- REQ-6: Without `.claude-docker/setup.sh`, and under `--ephemeral`, `run.sh` SHALL behave exactly as before: no extra container, volume or env.

## Scenarios

### Scenario: First launch with a new script
- **Given** a project whose repo gains `.claude-docker/setup.sh` installing `sqlcmd` into `$CLAUDE_DOCKER_PROJECT_TOOLS/bin`
- **When** the owner launches its box and answers `y` to the shown script
- **Then** the setup container runs it, the box starts, and `command -v sqlcmd` is `/opt/project-tools/bin/sqlcmd`

### Scenario: Unchanged relaunch
- **Given** an approved script whose stamp matches
- **When** the box is launched again
- **Then** no setup container runs and no prompt appears

### Scenario: Agent edits the script
- **Given** a session that changed `setup.sh` in the repo
- **When** the box is next launched
- **Then** the owner sees the diff against the approved copy and nothing runs without `y`

### Scenario: Box tries to poison the cache
- **Given** a running box
- **When** it writes under `/opt/project-tools`
- **Then** the write fails (read-only mount)

### Scenario: cd-up with a changed script
- **Given** a changed script and a launch with no TTY
- **When** the box starts
- **Then** setup is skipped with a one-line notice naming how to approve, and the box starts on the old cache

## Out of scope

- Moving the 0003 SQL tooling out of the image.
- Setup scripts in second and later workspaces; only the first workspace's runs.
- Env vars beyond `PATH`: a tool needing one (e.g. `DOTNET_ROOT`) ships a wrapper in `bin/` that sets it.
- System packages: the setup container is unprivileged like the box, so `apt-get` is unavailable by design; scripts install userland binaries (tarballs, `uv tool`, `go install` with `GOPATH` inside the volume).
