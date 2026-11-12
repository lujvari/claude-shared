## Why

After a laptop reboot or power-down the owner reopens about a dozen Windows
Terminal tabs by hand and types `cd-x -- --continue` in each. Docker Desktop
already autostarts (switched on host-side 2026-11-10), so what is left is the
tab-by-tab relaunch.

## What Changes

- **New `launchers/cd-up`.** One command, run from WSL, that opens one Windows
  Terminal tab per box in the current window and resumes each box's last
  conversation. `cd-up` with no arguments opens the whole fleet; `cd-up rr cis`
  opens only the named boxes. The fleet list is hard-coded in the script: it
  barely changes, and editing one line beats any registry.
- **Preflight, once, before any tab.** Wait for `docker info` to succeed
  (bounded, 180 s), then run `op whoami` once. If Docker never comes up, or
  1Password is not authenticated, stop with one clear line and open nothing.
  Every box would otherwise fail its own `op read` and abort in its own tab.
- **One `wt.exe` call per box, staggered ~3 s.**
  `wt.exe -w 0 new-tab --title cd-X wsl.exe -e bash -lic '<cmd>'`.
  - `bash -lic`: `-l` because `~/bin` reaches PATH through `~/.profile`; `-i`
    because the 1Password token pointer is read in `~/.bashrc`.
  - Staggered because `op read` has a 5 s timeout (`run.sh` `OP_READ_TIMEOUT`)
    and the credential gate before `docker run` aborts on any failed read.
    A dozen simultaneous launches at boot is how that timeout gets hit.
  - The tab drops to a shell when the box exits or fails (`exec bash`), so a
    failed launch stays visible and can be retried with the up-arrow.
  - **No `;` inside `<cmd>`.** `wt.exe` treats `;` as its subcommand
    separator, including inside an argument, so `<cmd>` is
    `cd-X -- --continue || true && exec bash`, which chains without one.
    That removes the question rather than relying on the quoting to survive.
- **Unknown name = error before any tab opens**, listing the valid names.
- **Opt-in `--yolo`.** `cd-up --yolo [box...]` passes `--yolo` to every box it
  opens (`cd-X --yolo -- --continue || true && exec bash`, still no `;`). A
  plain `cd-up` never adds it: a `--yolo` box can use every credential its
  launcher mounts without a permission prompt, so that stays a per-run choice.
  Flags come before box names; an unknown flag exits 2 before anything runs.

Out of scope (deliberately; a critic review dropped these as overcomplicated):

- A box registry, a respawn loop, a "stale box" indicator.
- Docker Desktop autostart (done host-side).
- `--yolo` as the default, or baked into any launcher.
- Raising `CLAUDE_DOCKER_OP_TIMEOUT` for these launches; the stagger is the fix.

Known limit, documented rather than fixed: `--continue` resumes the newest
session in the box's working directory. Two boxes from the same launcher, or a
headless `claude -p` run in that workspace since, can make a tab resume the
wrong conversation. A box with no previous conversation falls through to the
shell, from where a plain `cd-X` starts fresh.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `launchers`: adds the fleet relaunch command.

## Impact

- **Code**: new `launchers/cd-up`. No change to `run.sh`, `_lib.sh` or any
  existing launcher.
- **Docs**: `launchers/README.md`, a short "After a reboot" section and the
  install loop already picks up `cd-up` (it globs `cd-*`).
- **Install**: on the host afterwards, the existing `ln -sfn` loop into
  `~/bin`.
