## 1. run.sh

- [x] 1.1 Initialize `WITH_ADO=0` next to the other opt-in flags
- [x] 1.2 Add `--ado` to the help heredoc with a one-line description
- [x] 1.3 Add `--ado) WITH_ADO=1 ;;` to the flag-parsing case statement
- [x] 1.4 Append `AZURE_DEVOPS_EXT_PAT` to `ENV_VARS` when `WITH_ADO=1` so the existing forwarding loop picks it up only when set on the host
- [x] 1.5 When `--ado` is set, append `-e CLAUDE_DOCKER_ADO_HOSTS=<csv>` to `ENV_ARGS` (default `dev.azure.com`, honor `CLAUDE_DOCKER_ADO_HOSTS` as an override)
- [x] 1.6 Append `"ado"` to `DOCKER_FLAGS` when `WITH_ADO=1` so the statusline tag surfaces it

## 2. entrypoint.sh

- [x] 2.1 After the existing `inject_insteadof` call for GitLab, add a third call for Azure DevOps: `inject_insteadof "${AZURE_DEVOPS_EXT_PAT:-}" "${CLAUDE_DOCKER_ADO_HOSTS:-dev.azure.com}"`. No helper refactor needed — Azure Repos accepts the hard-coded `oauth2:` username paired with a PAT.

## 3. Smoke tests

- [ ] 3.1 `docker build -t claude-code:local ./claude-docker` succeeds (no Dockerfile changes — sanity rebuild only)
- [ ] 3.2 `--ado` with explicit token: `docker run --rm -e AZURE_DEVOPS_EXT_PAT=fakepat -e CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com claude-code:local sh -c 'git config --system --get-all url.https://oauth2:fakepat@dev.azure.com.insteadOf'` prints `https://dev.azure.com`
- [ ] 3.3 `--ado` with custom host list: `docker run --rm -e AZURE_DEVOPS_EXT_PAT=fakepat -e CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com,myorg.visualstudio.com claude-code:local sh -c 'git config --system --list | grep insteadOf'` shows both rewrites
- [ ] 3.4 No-flag invariant unchanged: `claude-docker ~/repo` without `--ado` does not export `AZURE_DEVOPS_EXT_PAT` even if set on the host, and `/etc/gitconfig` has no `dev.azure.com` insteadOf rewrite
- [ ] 3.5 Statusline tag surfaces: `claude-docker --ado ~/repo` prints `docker:ado` (or `docker:gh,ado` when combined) in the prepended status fragment
- [ ] 3.6 End-to-end: with `AZURE_DEVOPS_EXT_PAT` set on the host to a real PAT with `Code: Read` scope, `claude-docker --ado ~/some-ado-repo` then `git ls-remote https://dev.azure.com/<org>/<proj>/_git/<repo>` inside the container succeeds without prompting

## 4. Documentation

- [x] 4.1 Add `--ado` row to the Credential opt-in table in README
- [x] 4.2 Add `--ado` row to the Auth model table in README
- [x] 4.3 Extend the Threat model "Exposed" bullet to mention `AZURE_DEVOPS_EXT_PAT` and `--ado` as a new insteadOf injection surface
- [x] 4.4 Extend the "Private git module fetch" Scope paragraph to mention `--ado` with `dev.azure.com` as the default host
- [x] 4.5 Add `ado` to the example statusline-tag list

## 5. Validation

- [ ] 5.1 `openspec validate add-ado-support --strict` exits 0
- [x] 5.2 `claude-docker --help` shows `--ado` in the flag list
- [x] 5.3 Spot-check that the `--ephemeral` interaction stays clean: under `--ado --ephemeral`, the entrypoint still writes `/etc/gitconfig` (which lives in the writable layer, not the named volume), so ephemerality is preserved
