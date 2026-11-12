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
cd-up                    # every box, one Windows Terminal tab each, resumed
cd-up rr cis             # only those
cd-up --yolo [box...]    # pass --yolo to every box opened
```

`--yolo` is opt-in and never the default: a `--yolo` box can use whatever
credentials its launcher mounts without a permission prompt.

Run it from WSL inside Windows Terminal. It waits for Docker (up to 180 s),
checks `op whoami` once and stops cleanly if 1Password isn't signed in, then
opens one tab per box ~3 s apart so the boxes' `op read`s don't time out
together. A tab whose box fails stays open at a shell: retry with the up-arrow.

The fleet is the `boxes=(...)` line at the top of `cd-up`; add a new launcher
there too. `--continue` resumes the newest session in the box's working
directory, so a second box from the same launcher, or a `claude -p` run there
since, can make a tab resume the wrong conversation.

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

A launcher that brings up its project's test database (`cd-brain`, `cd-mep`)
calls `cd_test_db_hold <container>` before the `up`, and ends with
`cd_test_db_run <container> <flags> "$ws" "$@"` in place of the `exec`. The
last box of that project to exit then stops the database: `docker stop`, not
`down`, so the data survives and the next launch restarts it. A second box of
the same project keeps it running. The test DBs are therefore down between
sessions, so a host-side test run brings its own up. The mechanism (a shared
`flock`) is documented in `_lib.sh`.

Work that spans several trees calls `cd_workspace` once per tree and passes
them all; the first becomes the box's working directory (see `cd-asr`,
`cd-inat`). A tree passed twice — a launcher default plus a `+PATH` naming it
again — is mounted once; two *different* trees with the same basename still
fail run.sh's collision check.

The dev root is derived in `_lib.sh` from the checkout's own location, four
levels above this directory — nothing to configure when the clone moves.
