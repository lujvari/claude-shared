Plan v2. v1 assumed the rules live under WSL `$HOME`; this box's `CLAUDE.md`
is mounted from `C:\`, so the source is now derived from the config dir. v1
also missed runc creating `~/.inat` as root.

## 0. Host facts first (WSL, by the owner)

- [x] 0.1 Find the real config dir and its rules: `d=$(readlink -f "${CLAUDE_DOCKER_CONFIG_DIR:-$HOME/.claude}"); r="$(dirname "$d")/.inat/rules"; echo "$r"; test -d "$r" && find "$r" -type l | wc -l || echo MISSING`. Expected: a path under `/mnt/c/Users/...` and `0`. `MISSING` means inat wrote somewhere else; stop and locate it before step 1. A non-zero link count means switching to `cp -RL` staging (plan v3).

## 1. run.sh

- [x] 1.1 After the `CLAUDE.md` mount (~run.sh:1583): `rules_home=$(cd "$CLAUDE_CONFIG_DIR" 2>/dev/null && pwd -P)`, then `${rules_home%/*}` for the parent. `cd`/`pwd -P` resolves symlinks on bash 3.2/macOS without `readlink -f`. If `"$rules_home/.inat/rules"` is a directory, append `-v "...:/home/claude/.inat/rules:ro"`. Otherwise, if `grep -qF '~/.inat/rules/' "$CLAUDE_CONFIG_DIR/CLAUDE.md"`, print one warning to stderr in the style of the existing `run.sh` warnings, naming the path.
- [x] 1.2 `--claude-dir` help (run.sh:272-274): add "inat user rules (<parent>/.inat/rules)" to the list of things it affects.
- [x] 1.3 Proof in the box: `bash -n run.sh` exits 0, and `grep -nF '/.inat' run.sh` shows a single mount target, `/home/claude/.inat/rules`.

## 2. Dockerfile

- [x] 2.1 Add `/home/claude/.inat` and `/home/claude/.inat/rules` to the `install -d -o 1000 -g 1000` list (Dockerfile:579).
- [x] 2.2 README one-off migration (README.md:655): add `/r/.inat` to the `mkdir -p` list.

## 3. README

- [x] 3.1 "Host config parity": add a `~/.inat/rules/` row (inat user rules, from the config dir's parent, mounted at `/home/claude/.inat/rules`). Reword the intro so it no longer says every item lands under `/home/claude/.claude/`.

## 4. Smoke tests (WSL, by the owner, after the image rebuild)

The owner runs one WSL heredoc and pastes the output back. Present and absent cases use `--claude-dir=<tmp>/.claude`, so the real `~/.inat` is never touched. Real auth still comes from volumes and the env file, which `--claude-dir` does not change.

- [x] 4.1 Real config: `/home/claude/.inat/rules` is mounted. The host dir was empty on 2026-11-16 (`inat --user` had not yet written files), so the content comparison moved to 4.2.
- [x] 4.2 `--claude-dir=<tmp>/.claude` with `<tmp>/.inat/rules/x.md` and `<tmp>/.inat/config.json`: `x.md` is present, and `grep ' /home/claude/.inat' /proc/mounts` prints exactly one line, ending at `/rules`. Proves "follows --claude-dir" and "only rules".
- [x] 4.3 In that box, `touch /home/claude/.inat/rules/y` fails with "Read-only file system".
- [x] 4.4 `--claude-dir` with no `.inat` and a `CLAUDE.md` without pointers: no inat output, and `/proc/mounts` has nothing at `.inat/rules`.
- [x] 4.5 Same, but `CLAUDE.md` contains `~/.inat/rules/a.md`: exactly one warning naming `<tmp>/.inat/rules`, and the box starts.
- [x] 4.6 `--ephemeral` with the 4.2 `--claude-dir`: rules are present, and `touch /home/claude/.inat/cache/probe` succeeds (needs `mkdir -p` of `cache` first; it must not fail with EACCES on `.inat`).
- [x] 4.7 `--ro` with the real config: rules are present.

## 5. Validation and hand-off

- [x] 5.1 `openspec validate add-inat-rules-mount --strict` exits 0.
- [x] 5.2 Commit to `main` and push.
- [ ] 5.3 Post the result to `host` and ask it to relay to the inat box (`sbp.ai.inat`); a box can only post to `host`. Close bus message `20261116T114253Z-38fbc7`.
