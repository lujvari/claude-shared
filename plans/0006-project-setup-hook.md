# Plan 0006 — per-project setup hook

**Spec:** specs/0006-project-setup-hook.md
**Effort:** medium
**Status:** draft

## Approach

A pre-step in `run.sh`, after workspaces and `box_key` are resolved and before the main `docker run`. Same pattern as the stage broker's approve-on-change (0002): the host holds the approved copy, the box can't touch it. The setup container gets nothing but the script directory and the tool volume, so an approved-but-malicious script still sees no credential and no home volume; the box then sees the result read-only, so a session can't plant a binary for the next launch.

Why a separate container rather than running it in the entrypoint: the box carries forwarded tokens and the home volume, and the entrypoint would run the script with them, before the owner sees anything.

## Changes

- `Dockerfile` — pre-create `/opt/project-tools` owned by 1000:1000 (an empty named volume copies the mountpoint's ownership; without it the uid-1000 setup container can't write).
- `lib/setup.sh` (new, sourced by `run.sh` like `lib/stage.sh`) — `setup_approved KEY SCRIPT`, `setup_prompt KEY SCRIPT` (full text or `diff -u` against the approved copy; `y` stores the copy, mode 0600), `setup_run KEY WORKSPACE` (stamp check, one-shot `docker run`, `timeout 900`, log to `/opt/project-tools/setup.log`, stamp `sha256 image-id` on exit 0).
- `run.sh` — `--setup-refresh` flag and help text; call the pre-step; add the volume (`:ro`), `PATH` and `CLAUDE_DOCKER_PROJECT_TOOLS` to the box when the volume exists; skip all of it under `--ephemeral`.
- `entrypoint.sh` — prepend `/opt/project-tools/bin` to `PATH` before `exec` when it exists (an `-e PATH` from `run.sh` would replace the image's PATH).
- `lib/test_setup.py` (new) — unit tests with a stub `docker`, as `test_stage.py` does.
- `README.md` — a "Project tools" section: the file, the approval prompt, what the script can and can't do, `--setup-refresh`.
- `specs/CURRENT.md` — lines for 0006 at closeout.

## Steps

1. `lib/setup.sh` + `lib/test_setup.py`: approval (unapproved, approved, changed), stamp skip, failure path, no-TTY skip. Proof: tests pass.
2. `run.sh` wiring + `entrypoint.sh` PATH + Dockerfile mountpoint. Proof: `run.sh --dry-run` (or the stub-docker harness) shows the setup container's args (no `-e` credentials, no home volume, `:ro` script dir) and the box's `:ro` tool mount.
3. Live, on WSL after an image rebuild: a scratch project with a setup.sh that drops a `hello` script into `bin/`. Proof: first launch prompts, `y`, box has `hello` on PATH; relaunch has no prompt and no setup container; `touch /opt/project-tools/x` in the box fails; edit the script, relaunch shows the diff; non-TTY launch skips with the notice.
4. README, CURRENT.md, closeout.

## Acceptance Checklist

- [ ] REQ-1: setup container args carry no credential env/file and no home volume; script dir `:ro`.
- [ ] REQ-2: unapproved/changed script prompts with full text/diff; no-TTY skips; approved copy is host-side, 0600.
- [ ] REQ-3: matching stamp skips the container; image rebuild re-runs; `--setup-refresh` empties and re-runs.
- [ ] REQ-4: box has the volume `:ro`, `bin/` first on `PATH`, `CLAUDE_DOCKER_PROJECT_TOOLS` set.
- [ ] REQ-5: failing script prints status and log tail, no stamp, box starts.
- [ ] REQ-6: no script, or `--ephemeral`: docker args identical to before.
- [ ] Rigor gates run before step 1.
