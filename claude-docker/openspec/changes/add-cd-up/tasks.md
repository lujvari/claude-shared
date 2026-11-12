## 1. launchers/cd-up

- [x] 1.1 Header comment (what it is, why one `wt.exe` per box, why `bash -lic`, why the stagger, why no `;`, the `--continue` limit). `set -euo pipefail`. Hard-coded `boxes=(...)`: all 14 current launchers (owner, 2026-11-11).
- [x] 1.2 Argument handling: none = all; otherwise each name must be in the list, else print the unknown name(s) plus the valid list and exit 2 before anything else runs. `-h`/`--help` prints usage.
- [x] 1.3 Preflight: poll `docker info >/dev/null 2>&1` every 2 s up to 180 s (`CD_UP_DOCKER_WAIT` overrides); then `op whoami >/dev/null 2>&1` once. Each failure: one line, exit 1.
- [x] 1.4 Per box: `wt.exe -w 0 new-tab --title "cd-$b" wsl.exe -e bash -lic "cd-$b -- --continue || true && exec bash"`, then `sleep 3` between boxes (`CD_UP_STAGGER` overrides). Print `cd-up: opened cd-$b` per tab.

- [x] 1.5 `--yolo`: parse leading options (`--yolo`, `-h`/`--help`; any other `-*` = exit 2 with usage) before validating box names; with `--yolo` the tab command becomes `cd-$b --yolo -- --continue || true && exec bash`. Header comment: why it is opt-in.

## 2. Docs

- [x] 2.1 `launchers/README.md`: "After a reboot" section: `cd-up`, `cd-up rr cis`, the preflight, editing the list, the `--continue` limit.
- [x] 2.2 README "After a reboot": `cd-up --yolo [box...]`, and that a `--yolo` box can use whatever credentials it mounts, hence opt-in.

## 3. Proof

- [x] 3.1 In-box, with shims on PATH (no `wt.exe`, `docker` or `op` in the box): fake `wt.exe`, `docker`, `op` and `sleep` that log their argv. Check: (a) no args = one `wt.exe` call per listed box, in order, each argv with no `;`; (b) `cd-up rr cis` = exactly those two; (c) unknown name = exit 2, no `docker`/`wt.exe` call; (d) `op whoami` failing = exit 1, no `wt.exe` call; (e) `docker info` failing with a short wait = exit 1, no `op`/`wt.exe` call. Harness passes 6/6 (plus `--help` opens nothing). Scratch harness, not committed.
- [x] 3.5 Extend the 3.1 harness: (g) no flag = no tab argv has `--yolo`; (h) `--yolo` = every tab argv has it, none contains `;`; (i) `--yolo rr cis` = exactly those two, with `--yolo`; (j) `--yolp rr` = exit 2, no `docker`/`op`/`wt.exe` call.  Passes 4/4 alongside the original 6, plus (k) `rr --yolo` = rejected as an unknown box (flags must come first).
- [x] 3.2 `bash -n` and `shellcheck -s bash` (shellcheck-py in a scratch venv) clean on `cd-up`.
- [ ] 3.3 Live on WSL (owner): `cd-up` with two boxes opens two titled tabs and both resume their conversation.
- [ ] 3.4 Live on WSL (owner): with `op` unauthenticated (e.g. `OP_SERVICE_ACCOUNT_TOKEN= cd-up rr`), it stops with the clean line and opens nothing.

## 4. Validation

- [x] 4.1 `openspec validate add-cd-up --strict` exits 0
