## 1. run.sh

- [x] 1.1 Initialize `WITH_ADO_ADMIN=0`
- [x] 1.2 Add `--ado-admin` to the help heredoc
- [x] 1.3 Add `--ado-admin) WITH_ADO_ADMIN=1 ;;` to the case statement
- [x] 1.4 Append `AZURE_DEVOPS_ADMIN_PAT` to `ENV_VARS` when `WITH_ADO_ADMIN=1`
- [x] 1.5 op-read fallback via `CLAUDE_DOCKER_ADO_ADMIN_OP_REF`; include in the preflight survey
- [x] 1.6 Append `"ado-admin"` to `DOCKER_FLAGS`
- [x] 1.7 `cred_require --ado-admin AZURE_DEVOPS_ADMIN_PAT`

## 2. entrypoint.sh

- [x] 2.1 No changes. The git credential helper installed for `--ado` keeps reading `AZURE_DEVOPS_EXT_PAT`.

## 3. Launchers

- [x] 3.1 `cd-ct --admin` alias added (0a1dd4a) and then removed (96e3f13); no launcher passes `--ado-admin` by default

## 4. Smoke tests

Not run as part of this retroactive record; the 0a1dd4a commit message records no verification.

- [ ] 4.1 `--ado --ado-admin` forwards both PATs; the git credential helper still answers with `AZURE_DEVOPS_EXT_PAT`
- [ ] 4.2 Op-ref fallback yields a non-empty `AZURE_DEVOPS_ADMIN_PAT`
- [ ] 4.3 No-flag invariant: `--ado` alone does not forward `AZURE_DEVOPS_ADMIN_PAT`
- [ ] 4.4 Fail closed: `--ado-admin` with no source exits non-zero before `docker run`

## 5. Documentation

- [x] 5.1 Credential opt-in row in README (character repaired in d385738)
- [x] 5.2 Auth-model row in README
- [ ] 5.3 `ado-admin` in the README statusline-tag list and `AZURE_DEVOPS_ADMIN_PAT` in the threat-model "Exposed" bullet (not done; neighbours list these; left as found)

## 6. Validation

- [ ] 6.1 `openspec validate add-ado-admin-support --strict` exits 0 (not run)
- [x] 6.2 `claude-docker --help` shows `--ado-admin`
