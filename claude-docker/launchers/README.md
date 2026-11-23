# Launchers

One executable per work type, each forwarding **only** the credentials that
kind of work needs. A prompt-injected repo can then exfiltrate a narrower set
of tokens than a kitchen-sink launch would expose: one flag = one credential in
the blast radius. Mounts are scoped per launcher for the same reason — a
session can only reach what is mounted.

Each file is the command name itself (`cd-ct`, not `cd-ct.sh`) so it can be
symlinked onto `PATH`.

## Install

```sh
L=/mnt/c/dev/tools/claude-shared/claude-docker/launchers
for n in "$L"/cd-*; do ln -sfn "$n" ~/bin/"$(basename "$n")"; done
```

`~/bin` is added to `PATH` by stock `~/.profile`, so **no shell rc defines
anything** — no functions, no aliases, no `DEV` to export. That is deliberate:
a shell function only exists in shells started after it was edited, and the
launchers are also the thing most likely to change.

`_lib.sh` is sourced, not a command; don't symlink it.

## Usage

```sh
cd-ct                    # launch a Control Tower session
cd-ct --yolo             # wrapper flags pass through
cd-ct -- --resume        # everything after -- goes to claude verbatim
```

Switching work does not require closing the current container: open another
terminal and run a different launcher. Concurrent containers are supported
(give two sessions on the same repo separate worktrees — see the main README),
so you never trade a running session to change flags.

## After a reboot

```sh
cd-up                    # every box not running, a tab each, resumed
cd-up mep cis            # only those
cd-up --work [box...]    # snap new windows to the work desk (--home)
cd-up --yolo [box...]    # pass --yolo to every box opened
```

`--yolo` is opt-in and never the default: a `--yolo` box can use whatever
credentials its launcher mounts without a permission prompt.

Run it from WSL inside Windows Terminal. It waits for Docker (up to 180 s),
skips every box that is already running (`cd-up: skipped cd-cis (already
running)`, named boxes too; run `cd-cis` itself for a second session), checks
`op whoami` once and stops cleanly if 1Password isn't signed in, then opens one
tab per box ~3 s apart so the boxes' `op read`s don't time out together. A tab
whose box fails stays open at a shell: retry with the up-arrow.

The tabs land in three windows, one per screen quarter: `cd-q1` (apg, asr),
`cd-q3` (tools, dev, mep) and `cd-q4` (brain, cis, ct, inat). An open one
just gets the tab. Plain `cd-up` leaves placing new windows to Windows.
`--work` or `--home` snaps each window the run creates to exactly that desk's
rectangle for its quarter, through the Windows API (`_snap.ps1`, run in
Windows PowerShell). Only those windows move: a window that was already open,
the browser and HELM stay put. A snap that fails prints
`cd-up: could not place cd-q3 (...)`; the tabs open anyway.

The groups (`q1=(...)` and the rest) and each desk's rectangles (`rect_of`,
X Y W H in physical pixels) are at the top of `cd-up`; add a new launcher to a
group, and a new desk as three more lines there. A desk with no rectangles yet
says so and opens unplaced; the wrong flag can put a window off-screen.

The running check reads the `claude-docker.box` label `run.sh` puts on each
container. Containers started before that label existed don't have it, so start
the first `cd-up` after updating with no box up. A box still starting has no
container yet: running `cd-up` again while the first run is opening tabs can
open it twice. A tab whose box has exited is not a running box either.
`--continue` resumes the newest session in the box's working directory, so a
`claude -p` run there since can make a tab resume the wrong conversation.

## Adding one

```sh
#!/usr/bin/env bash
# claude-docker launcher: <what this is, and why these flags>
set -euo pipefail
. "$(dirname "$(readlink -f "$0")")/_lib.sh"
cd_workspace "relative/path/from/dev/root"
exec "$CD_RUN" --claude-auth <flags> "$ws" "$@"
```

Two rules:

- **`"$@"` stays last.** Everything after `--` is forwarded verbatim to
  `claude`, so a workspace path sitting after `"$@"` is swallowed as a claude
  argument and the mount silently falls back to `$PWD`.
- **No credentials here.** Tokens and `op://` refs live in
  `~/.config/claude-docker/env`, which `run.sh` loads itself; see the comment
  above `CD_ENV_FILE` in `run.sh` for why that is not a shell rc. A launcher
  names *which* credentials to forward, never their values.
  A box that needs a different credential from the default sets a named
  profile and its `op://` ref, a pointer, not a value (`cd-apg` for ADO,
  `cd-inat` for GitHub); `run.sh` then ignores the default sources.

A launcher that brings up its project's test database (`cd-brain`, `cd-mep`)
calls `cd_test_db_hold <container>` before the `up`, and ends with
`cd_test_db_run <container> <flags> "$ws" "$@"` in place of the `exec`. The
last box of that project to exit then stops the database: `docker stop`, not
`down`, so the data survives and the next launch restarts it. A second box of
the same project keeps it running. The test DBs are therefore down between
sessions, so a host-side test run brings its own up. The mechanism (a shared
`flock`) is documented in `_lib.sh`.

Work that spans several trees calls `cd_workspace` once per tree and passes
them all, keeping each path in a named variable; the first becomes the box's
working directory and sets its mailbox and venv keys (see `cd-asr`,
`cd-inat`, `cd-tools`). A tree passed twice — a launcher default plus a
`+PATH` naming it again — is mounted once; two *different* trees with the same basename still
fail run.sh's collision check.

`cd-mep`, `cd-brain` and `cd-board` mount `laslo/architecture`, the LikeC4
model of those three services, second: a session that changes an
integration, data store, MCP connection or deployment there updates the
model too. Up to three boxes then share that one checkout, so commit model
edits by path, never `git add -A` (see "Concurrent Claude sessions on one
checkout" in the main README).

The dev root is derived in `_lib.sh` from the checkout's own location, four
levels above this directory — nothing to configure when the clone moves.
