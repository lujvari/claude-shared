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
ln -sfn "$L/cd-cis" ~/bin/cd-asr      # same tree; tenant = AWS_PROFILE
ln -sfn "$L/cd-cis" ~/bin/cd-aegon
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
(worktree-guard handles shared checkouts), so you never trade a running session
to change flags.

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

The dev root is derived in `_lib.sh` from the checkout's own location, four
levels above this directory — nothing to configure when the clone moves.
