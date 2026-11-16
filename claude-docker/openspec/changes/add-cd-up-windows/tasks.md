## 1. Box label

- [x] 1.1 `launchers/_lib.sh`: `export CLAUDE_DOCKER_BOX=$(basename "$0")`, next to the bus and Brain exports, with a comment (who reads it, why `$0`: every launcher sources this file, so `$0` is the `cd-<name>` symlink on PATH). Set unconditionally, never inherited.
- [x] 1.2 `run.sh`: `--label "claude-docker.box=${CLAUDE_DOCKER_BOX:-}"` on the `docker run` line. Always present, empty when run.sh is called directly (the docker run line takes no conditionally-empty array, see the comment above MOUNT_ARGS). Mention `CLAUDE_DOCKER_BOX` in run.sh's env help next to `CLAUDE_DOCKER_BUS_DIR`.

## 2. launchers/cd-up

- [ ] 2.1 Replace `boxes=(...)` with three groups and their geometry, one place to edit: `q1=(apg asr)`, `q3=(tools dev mep)`, `q4=(brain cis ct inat)`, each with `--pos X,Y --size C,R` placeholders until 4.2. `boxes` is derived from the groups, so the unknown-name check and `--help` keep working unchanged. A `window_of <box>` lookup returns the window name (`cd-q1|cd-q3|cd-q4`). Named boxes are de-duplicated, keeping first-seen order.
- [ ] 2.2 After the Docker wait: for each requested box, `docker ps -q --filter "label=claude-docker.box=cd-$b"`; non-empty = print `cd-up: skipped cd-$b (already running)` and drop it. `docker ps` failing = one line `cd-up: could not list running boxes` and exit 1, explicitly (not a silent `set -e` exit). None left = `cd-up: nothing to open` and exit 0, before `op whoami`. The stagger runs between opened tabs only, never before the first.
- [ ] 2.3 Per box: `wt.exe -w <group> <geometry> new-tab --title "cd-$b" wsl.exe -e bash -lic "..."`, same tab command as today. Header comment: the quarter layout, that geometry applies only when the named window is new, `--size` is in character cells, the off-screen risk with one monitor, and the skip rule (named boxes too; run `cd-<b>` directly for a second session). Keep the `--continue` known-limit note: the skip only sees labelled containers, and a headless `claude -p` run still counts as newest.

## 3. Docs

- [ ] 3.1 `launchers/README.md` "After a reboot": the three windows, the skip line, where to edit groups and geometry, the starting-box race and dead-tab limits, and that the first run after this ships should start with no box up (older containers carry no label).

## 4. Proof

- [ ] 4.1 In-box shim harness (as in add-cd-up 3.1, scratch, not committed): fake `wt.exe`, `docker`, `op`, `sleep` logging argv; fake `docker ps` answers per label from a fixture. Check: (a) no args = 9 `wt.exe` calls, each with the right `-w cd-q1|cd-q3|cd-q4` and geometry, no `;`; (b) `cd-up mep cis` = `-w cd-q3` then `-w cd-q4`; (c) `cis` running = skipped line, 8 calls, both for no args and for `cd-up cis mep`, and no `sleep` before the first opened tab; (c2) `docker ps` failing = exit 1 with its line, no `op`/`wt.exe`; (c3) `cd-up mep mep` = one call; (d) all running = 9 skipped lines, exit 0, no `op` call; (e) `op` failing with one box not running = exit 1, no `wt.exe`; (f) unknown name / unknown option / docker never up = as before; (g) `--yolo` still reaches every tab. `bash -n` and shellcheck clean on `cd-up`, `_lib.sh`, `run.sh`.
- [ ] 4.2 Live on WSL (owner): print the screens' working areas from PowerShell, then set the three geometries in `cd-up` from them; `cd-up` from a clean desktop puts three windows roughly in Q1, Q3 and Q4 with the right tabs, each resuming. Adjust `--size` until the fit is acceptable. `wt.exe -w <name> --pos --size new-tab` was confirmed by hand beforehand (owner, 2026-11-16): new window placed, second call joined it unmoved.
- [ ] 4.3 Live on WSL (owner): with the fleet up, `cd-up` again prints nine skipped lines and opens nothing; `docker ps --filter label=claude-docker.box=cd-cis` lists exactly one container, and the same holds for `cd-mep` (the test-DB launcher path); close the `cd-cis` tab's box, then `cd-up cis` adds its tab to the open `cd-q4` window and opens no new window.

## 5. Validation

- [ ] 5.1 `openspec validate add-cd-up-windows --strict` exits 0
