## Why

The owner works on two monitors, each split in halves, so four screen quarters
with a fixed job each:

- Q1: client work (`apg`, `asr`)
- Q2: HELM, the host session (not a box; not cd-up's business)
- Q3: `tools`, `dev` (notes), `mep`
- Q4: low-attention boxes (`brain`, `cis`, `ct`, `inat`)

`cd-up` opens every box as a tab in one window, so after each reboot the owner
drags tabs into three windows and snaps them into place by hand.

`cd-up` also opens a box that is already running. The second session in the
same workspace makes `--continue` liable to resume the wrong conversation.

## What Changes

- **One window per quarter.** The fleet list in `cd-up` becomes three groups,
  one per quarter. Each group opens in its own named Windows Terminal window
  (`cd-q1`, `cd-q3`, `cd-q4`, prefixed so they can't collide with a window
  the owner named). A window that already exists (cd-up run twice) gets the
  new tabs and keeps its place. `cd-up mep cis` still opens only those boxes, each in its own
  group's window.
- **Placement per desk.** The owner has two desks: work (two 2560x1440
  screens side by side) and home (layout not yet known). `--work` and
  `--home` pick that desk's pixel rectangle per window: once a group's
  window is new, `cd-up` snaps it to exactly that rectangle through the
  Windows API (PowerShell called from WSL), compensating for the invisible
  window border. Pixel-exact, not character cells: `wt.exe --size` only takes
  characters, which left the fit a cell off and needed tuning per desk (owner
  chose exact snap after trying it, 2026-11-16). Only windows this run
  created are ever moved: cd-up lists the terminal windows before opening a
  group's first tab and snaps the one that is new. A hotkey in the owner's
  AutoIt script was tried instead and dropped the same day: from outside, the
  three cd-up windows can't be told apart from every other terminal (Claude
  Code rewrites the titles), so it moved them all. No new window within a few
  seconds means the group window already existed: nothing is moved, nothing
  is printed. A snap that fails otherwise (PowerShell error) prints one
  warning line; the tabs still open and the window stays where Windows put
  it. Plain `cd-up`
  places nothing: the windows are grouped and Windows puts them where it
  likes, which is safe on any screen setup (owner, 2026-11-16). A desk whose
  geometry is not filled in yet behaves like plain `cd-up` and says so in one
  line. `--home` and `--work` together is an error.
- **Running boxes are skipped.** Every launched box's container carries a
  label naming its launcher. `cd-up` checks it after the Docker preflight and,
  for a box already running, prints `cd-up: skipped cd-<b> (already running)`
  and opens no tab. This holds for named boxes too (owner, 2026-11-16): a
  second session in a running box is opened by running `cd-<b>` directly.
  If every requested box is running, `cd-up` says so and exits 0 without
  checking 1Password. A box named twice opens once. If `docker ps` itself
  fails, `cd-up` stops with one line and opens nothing, rather than guess.

Out of scope:

- Moving a window that already existed before the run.
- Rectangles derived from the screen layout at run time; each desk's three
  rectangles are written into the script once.
- Detecting the monitor layout at run time. The owner picks the desk with a
  flag; the wrong flag (or `--work` on an undocked laptop) can place a window
  partly off-screen.
- Launching or placing HELM.
- A box that is still starting. Its label exists only once `docker run`
  executes, after the launcher's `op read`s (and a test-DB lock wait for
  `brain` and `mep`), so a second `cd-up` run during the first one's stagger
  can open it twice.
- Dead tabs: the shell a tab keeps after its box exits is not a running box,
  so a re-run opens a fresh tab next to it.
- Detecting containers started before this change: they carry no label. After
  a reboot nothing is running, which is the case cd-up is for. The first
  `cd-up` after this ships, with old boxes still up, would duplicate them;
  the README says to run it from a clean start.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `launchers`: cd-up groups boxes into positioned windows and skips running
  boxes; launched containers carry a label naming their launcher.

## Impact

- `launchers/cd-up`: grouped fleet, per-desk rectangles, running check.
- `launchers/_snap.ps1` (new): lists Windows Terminal windows, and snaps the
  one that appeared since a given list to a rectangle. Fed to `powershell.exe
  -EncodedCommand`, so no execution policy or Windows path is involved.
- `launchers/_lib.sh`: exports the launcher's name for run.sh.
- `run.sh`: one `--label` on `docker run`.
- `launchers/README.md`: the "After a reboot" section.
