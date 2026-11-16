<!-- Plan v2 (2026-11-16): placement rewritten for the AutoIt hotkey; v1 snapped from PowerShell inside cd-up. 1.x, 2.1-2.3 and 4.1 are unaffected. -->

## 1. Box label

- [x] 1.1 `launchers/_lib.sh`: `export CLAUDE_DOCKER_BOX=$(basename "$0")`, next to the bus and Brain exports, with a comment (who reads it, why `$0`: every launcher sources this file, so `$0` is the `cd-<name>` symlink on PATH). Set unconditionally, never inherited.
- [x] 1.2 `run.sh`: `--label "claude-docker.box=${CLAUDE_DOCKER_BOX:-}"` on the `docker run` line. Always present, empty when run.sh is called directly (the docker run line takes no conditionally-empty array, see the comment above MOUNT_ARGS). Mention `CLAUDE_DOCKER_BOX` in run.sh's env help next to `CLAUDE_DOCKER_BUS_DIR`.

## 2. launchers/cd-up

- [x] 2.1 Replace `boxes=(...)` with three groups and their geometry, one place to edit: `q1=(apg asr)`, `q3=(tools dev mep)`, `q4=(brain cis ct inat)`, each with `--pos X,Y --size C,R` placeholders until 4.2. `boxes` is derived from the groups, so the unknown-name check and `--help` keep working unchanged. A `window_of <box>` lookup returns the window name (`cd-q1|cd-q3|cd-q4`). Named boxes are de-duplicated, keeping first-seen order.
- [x] 2.2 After the Docker wait: one `docker ps --format` listing every running container's `claude-docker.box` label; a requested box among them = print `cd-up: skipped cd-$b (already running)` and drop it. `docker ps` failing = one line `cd-up: could not list running boxes` and exit 1, explicitly (not a silent `set -e` exit). None left = `cd-up: nothing to open` and exit 0, before `op whoami`. The stagger runs between opened tabs only, never before the first.
- [x] 2.3 Per box: `wt.exe -w <group> <geometry> new-tab --title "cd-$b" wsl.exe -e bash -lic "..."`, same tab command as today. Header comment: the quarter layout, that geometry applies only when the named window is new, `--size` is in character cells, the off-screen risk with one monitor, and the skip rule (named boxes too; run `cd-<b>` directly for a second session). Keep the `--continue` known-limit note: the skip only sees labelled containers, and a headless `claude -p` run still counts as newest.

- [x] 2.4 `--work` / `--home`: one more leading option each, setting `desk`; both = usage error, exit 2. `geometry_of` becomes `geometry_of <desk> <group>` (case on `desk/group`) printing `--pos X,Y --size 120,40`, the point 40 px in from the quarter's top-left: work = `40,40`, `2600,40`, `3880,40`; home empty (prints nothing). 120x40 cells is ~1000x800 px (154 cells measured ~1280 px on 2026-11-16), so the centre stays well inside a 1280 px quarter. No desk = no geometry. A desk with no points prints `cd-up: no <desk> placement yet; windows unplaced` once. Usage line shows `[--work|--home] [--yolo]`. Header comment: rough placement here, exact snap by the AutoIt hotkey.
- [x] 2.5 `tools/autoit/MoveWindow.au3` (outside this repo, not git; spec and plan are this change): `HotKeySet("^{NUMPAD2}", "SnapShells")`. `SnapShells` takes the handles from the existing `_GatherTerminalHandles`, restores any minimised one, and for each: centre from `WinGetPos`, monitor work area via `DllCall` (`MonitorFromWindow` + `GetMonitorInfoW`, no `#include`, keeping the script dependency-free), `WinActivate` + `WinWaitActive`, then the existing `MoveLeft` or `MoveRight` by which half the centre is in. README: the hotkey row. Precedent: `BringShellsToFront` (same handle walk) and `MoveLeft`/`MoveRight` (same snap).

## 3. Docs

- [x] 3.1 `launchers/README.md` "After a reboot": the three windows, the skip line, where to edit groups and geometry, the starting-box race and dead-tab limits, and that the first run after this ships should start with no box up (older containers carry no label).

## 4. Proof

- [x] 4.1 In-box shim harness (as in add-cd-up 3.1, scratch, not committed): fake `wt.exe`, `docker`, `op`, `sleep` logging argv; fake `docker ps` answers per label from a fixture. Check: (a) no args = 9 `wt.exe` calls, each with the right `-w cd-q1|cd-q3|cd-q4` and geometry, no `;`; (b) `cd-up mep cis` = `-w cd-q3` then `-w cd-q4`; (c) `cis` running = skipped line, 8 calls, both for no args and for `cd-up cis mep`, and no `sleep` before the first opened tab; (c2) `docker ps` failing = exit 1 with its line, no `op`/`wt.exe`; (c3) `cd-up mep mep` = one call; (d) all running = 9 skipped lines, exit 0, no `op` call; (e) `op` failing with one box not running = exit 1, no `wt.exe`; (f) unknown name / unknown option / docker never up = as before; (g) `--yolo` still reaches every tab. `bash -n` and shellcheck clean on `cd-up`, `_lib.sh`, `run.sh`. Passes 18/18, incl. a `cd-cisx` decoy label and one `docker ps` per run (scratch harness; geometry still the 0,0 placeholder until 4.2).
- [x] 4.1b Extend the harness: no flag = no `--pos` in any `wt` argv; `--work` = `--pos 40,40|2600,40|3880,40 --size 120,40` by group on every argv; `--home` (empty) = the notice line and no `--pos`; `--home --work` = exit 2, no `docker`; `--work --yolo mep` = both applied. The AutoIt file is checked by eye (no AutoIt in the box) and live in 4.2. Passes 20/20 plus every exit code.
- [ ] 4.2 Live (owner), at work, after restarting MoveWindow.au3: open three empty test windows with the `--work` points (`wt.exe -w cd-t1 --pos 40,40 --size 120,40 new-tab`, and 2600 / 3880), press `Ctrl+Numpad2`: each fills exactly the half it was in, no gap or overlap, none moves to another half. Then at the next reboot, `cd-up --work` + `Ctrl+Numpad2` gives the fleet in Q1, Q3 and Q4, each tab resuming.
- [ ] 4.4 At home (owner): print the screens' working areas (same PowerShell line), fill in the three home points, `cd-up --home` + `Ctrl+Numpad2`.
- [ ] 4.3 Live on WSL (owner): with the fleet up, `cd-up` again prints nine skipped lines and opens nothing; `docker ps --filter label=claude-docker.box=cd-cis` lists exactly one container, and the same holds for `cd-mep` (the test-DB launcher path); close the `cd-cis` tab's box, then `cd-up cis` adds its tab to the open `cd-q4` window and opens no new window.

## 5. Validation

- [x] 5.1 `openspec validate add-cd-up-windows --strict` exits 0
