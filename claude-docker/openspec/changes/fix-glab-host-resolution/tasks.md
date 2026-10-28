## 1. run.sh

- [x] 1.1 Delete `_extract_glab_hosts` and its comment block. Set `glab_hosts="${CLAUDE_DOCKER_GITLAB_HOSTS:-}"` under `--glab`, and reword the "Compute host lists" comment so it no longer claims glab config is parsed. Proof: `grep -c _extract_glab_hosts run.sh` prints 0, and `bash -n run.sh` passes.
- [ ] 1.2 `[ "$WITH_GLAB" = "1" ] && ENV_VARS+=(GITLAB_TOKEN GITLAB_HOST)`. Proof: run.sh has no dry-run, so this is proven in 4.1, where `echo $GITLAB_HOST` in the box prints the sbp host.
- [x] 1.3 `--glab` help text: the host list comes from `CLAUDE_DOCKER_GITLAB_HOSTS` (default gitlab.com), and `GITLAB_HOST` is forwarded. Proof: `run.sh --help | grep -A8 -- --glab`.

## 2. Launchers

- [x] 2.1 `cd-cis`, `cd-inat`, `cd-asr`, `cd-ta`: `export GITLAB_HOST=sbp.gitlab.schubergphilis.com CLAUDE_DOCKER_GITLAB_HOSTS=sbp.gitlab.schubergphilis.com` before `exec`. Proof: `bash -n` on each, and `grep -c GITLAB_HOST` returns 1 for each.

## 3. Docs

- [x] 3.1 README `--glab` row: drop the "enumerated from glab config" sentence, and name `GITLAB_HOST` and the launcher defaults.

## 4. Verification (host / cd-inat box: needs Docker and the SBP token)

- [ ] 4.1 Launch `cd-inat`. In the box, `glab mr list` in the inat repo works with no extra env.
- [ ] 4.2 In the box, `git config --show-origin --get-regexp '^credential\..*helper'` shows sbp.gitlab only, with no gitlab.com and no `insteadOf`.
- [ ] 4.3 In the box, in sbp-ai/kits: create a scratch branch, push it, run `glab mr create --draft`, then close the MR and delete the remote and local branch. If GitLab refuses, stop and hand it to the owner to widen the token scope.
- [ ] 4.4 Plain `run.sh --glab <ws>` with neither variable set: no `CLAUDE_DOCKER_GITLAB_HOSTS` is forwarded, and the helper falls back to gitlab.com.

## 5. On archive

- [ ] 5.1 Fold `specs/external-cli-tools/spec.md` (this change) into the main spec. This replaces the stale `--glab` config-mount bullet and the "--glab grants read-only token access" scenario.
