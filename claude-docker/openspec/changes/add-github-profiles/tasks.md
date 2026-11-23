## 1. Profile resolver

- [x] 1.1 `lib/gh-profile.sh`: `gh_profile_resolve`, shaped like `ado_profile_resolve` (explicit returns, bash 3.2). No profile: return 0, touch nothing. Bad name: error, return 1. Profile without `--gh`: inert. Missing `CLAUDE_DOCKER_GITHUB_<NAME>_OP_REF`: error naming it, return 1. Otherwise set `GH_PROFILE` and `GH_OP_REF_VAR`, note and unset a host `GH_TOKEN`/`GITHUB_TOKEN` (never printing the value), export `CLAUDE_DOCKER_GITHUB_OP_REF` = the profile ref and `CLAUDE_DOCKER_GITHUB_HOSTS=github.com`.
- [x] 1.2 `lib/test_gh_profile.py`, shaped like `lib/test_ado_profile.py`: no profile passes through; profile ok replaces ref and hosts; host tokens dropped with a note that never contains the value; missing ref; bad names; profile without `--gh` inert. `python3 -m unittest lib/test_gh_profile.py` green, and `lib/test_ado_profile.py` still green.

## 2. run.sh

- [x] 2.1 Env-file loader skips `CLAUDE_DOCKER_GITHUB_PROFILE` (next to the ADO keys, `run.sh:631`).
- [x] 2.2 Source `lib/gh-profile.sh` and call `gh_profile_resolve || exit 1` under `--gh`, after the ADO resolve and before `ENV_VARS` (`run.sh:648-655`).
- [x] 2.3 Mask `/home/claude/.config/gh` when `--gh` is off **or** a profile is set (`run.sh:1722`).
- [x] 2.4 After the ADO profile check (`run.sh:1804`): a profile with no `GH_TOKEN` exits 1; `CLAUDE_DOCKER_OP_OPTIONAL` does not apply.
- [x] 2.5 `--help`: `--gh` names the profile; `CLAUDE_DOCKER_GITHUB_PROFILE` documented next to `CLAUDE_DOCKER_ADO_PROFILE`.
- [x] 2.6 `bash -n run.sh` (shellcheck is not installed in the box; not run).

## 3. Launcher and docs

- [x] 3.1 `cd-inat`: header comment covers GitHub; `export CLAUDE_DOCKER_GITHUB_PROFILE=inat`, `export CLAUDE_DOCKER_GITHUB_INAT_OP_REF="${CLAUDE_DOCKER_GITHUB_INAT_OP_REF:-op://claude-docker/inat-github-ro/credential}"`; `--gh` in the `exec` line. `bash -n`.
- [x] 3.2 README: "Named GitHub profiles" section after "Named ADO profiles"; the `--gh` table row points to it.
- [x] 3.3 launchers/README.md "No credentials here": a launcher may set a profile and its `op://` ref (a pointer) to pick a box-specific credential (`cd-apg`, `cd-inat`).

## 4. Proof in the box, through the real run.sh

Scratch dev tree: copy of `claude-docker/` (run.sh, lib/, launchers/), `sbp/ai/inat` and `sbp/ai/kits` dirs. Run under `env -i` with PATH = stub bin first, scratch HOME holding `.claude/.credentials.json` and a gh `hosts.yml` listing `github.com` and `ghe.example.com`. `CLAUDE_DOCKER_BRAIN=0`, `CLAUDE_DOCKER_NO_TOKEN_PROBE=1`. Stubs: `docker` logs its args and the values of `GH_TOKEN`, `GITHUB_TOKEN`, `CLAUDE_DOCKER_GITHUB_HOSTS` it was given via `-e` (fake values only); `op` answers `whoami`, and for `read` logs the ref and prints `tok:<item>`, failing for a ref containing `FAIL`. Scratch env file: `CLAUDE_DOCKER_GITHUB_OP_REF=op://claude-docker/github-pat/credential`, `GH_TOKEN=envfile-token`, `CLAUDE_DOCKER_GITLAB_OP_REF=op://claude-docker/gitlab-pat/credential`, `CLAUDE_DOCKER_GITHUB_PROFILE=inat`. Shell exports `GITHUB_TOKEN=shell-token`.

- [x] 4.1 `cd-inat`: `op read` logged exactly once for GitHub, with the inat ref; never `github-pat`. Box `GH_TOKEN=tok:inat-github-ro`, `GITHUB_TOKEN` absent, `CLAUDE_DOCKER_GITHUB_HOSTS=github.com`, a tmpfs on `/home/claude/.config/gh`, `GITLAB_HOST` and `CLAUDE_DOCKER_GITLAB_HOSTS` for sbp.gitlab. stderr never contains `envfile-token` or `shell-token`.
- [x] 4.2 `cd-inat` with `CLAUDE_DOCKER_GITHUB_INAT_OP_REF=op://x/FAIL/credential CLAUDE_DOCKER_OP_OPTIONAL=1`: exit 1, no `docker run` logged.
- [x] 4.3 `run.sh --gh` called directly with `CLAUDE_DOCKER_GITHUB_PROFILE=inat` and no profile ref (cd-inat always supplies its default): exit 1 naming `CLAUDE_DOCKER_GITHUB_INAT_OP_REF`, no `op read` logged.
- [x] 4.4 `cd-board` (plain `--gh`, scratch env file env file still holding `CLAUDE_DOCKER_GITHUB_PROFILE=inat`, no `GH_TOKEN` line): box gets `GH_TOKEN=tok:github-pat`, no gh tmpfs mask, hosts from the scratch `hosts.yml`. Proves the env file can't make a profile box and the default path is unchanged.

## 5. Proof on the host (WSL, by the owner)

- [ ] 5.1 Relaunch `cd-inat`; in the box: `gh api user --jq .login` prints `lujvarisbp` (the inat PAT's account, not the personal one).
- [ ] 5.2 `ls -A ~/.config/gh` shows no `hosts.yml`.
- [ ] 5.3 `glab auth status` still works for sbp.gitlab.
- [ ] 5.4 `gh api repos/schubergphilis/inat --jq .full_name`: works once the org owner has approved the token; 403/404 before.

## 6. Validation and hand-off

- [x] 6.1 `openspec validate add-github-profiles --strict` exits 0.
- [x] 6.2 `/simplify` on the diff (rigor Gate 8).
- [x] 6.3 Commit to `main` and push.
- [ ] 6.4 With the owner's OK, reply on bus message `20261123T094235Z-98797a`: what changed, relaunch `cd-inat`, the checks in 5. The owner decides when to close it.
