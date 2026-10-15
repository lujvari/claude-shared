## 1. run.sh

- [x] 1.1 Initialize `WITH_HETZNER_INFRA=0`
- [x] 1.2 Add `--hetzner-infra` to the help heredoc with the default ref and token-file path
- [x] 1.3 Add `--hetzner-infra) WITH_HETZNER_INFRA=1 ;;` to the case statement
- [x] 1.4 Append `HCLOUD_TOKEN` to `ENV_VARS` when `WITH_HETZNER_INFRA=1`
- [x] 1.5 Default `CLAUDE_DOCKER_HETZNER_OP_REF` and `CLAUDE_DOCKER_HETZNER_OP_TOKEN_FILE` with `${VAR-default}` so `""` is honoured
- [x] 1.6 Read the ref in a subshell with `OP_SERVICE_ACCOUNT_TOKEN` from the token file; never export it to the container or other reads
- [x] 1.7 Missing or empty token file → message naming the path, ref appended to `OP_FAIL_LOG`
- [x] 1.8 Token file without the `ops_` prefix → same handling (a4dcd30)
- [x] 1.9 With a token file, survey the flag only for the missing-`op` check, not the everyday `op whoami` preflight; with the file var `""`, join the regular preflight
- [x] 1.10 On read failure, hint that the infra service account was used
- [x] 1.11 Append `"hetzner-infra"` to `DOCKER_FLAGS`
- [x] 1.12 `cred_require --hetzner-infra HCLOUD_TOKEN`

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record. 84b1ec7 and a4dcd30 record op/docker-shim checks (including that no service-account token reached `docker run`); 84b1ec7 states the live vault, item and service account were not verified.

- [ ] 3.1 Against live 1Password: `cd-mep --yolo --hetzner-infra`, then `echo "len=${#HCLOUD_TOKEN}"` in the container prints a non-zero length
- [ ] 3.2 A dead everyday service-account token does not block a `--hetzner-infra`-only launch
- [ ] 3.3 Missing token file, non-`ops_` token file and revoked infra account each abort before `docker run`
- [ ] 3.4 No-flag invariant: `HCLOUD_TOKEN` is absent without the flag
- [ ] 3.5 `OP_SERVICE_ACCOUNT_TOKEN` is not present in the container environment

## 4. Documentation

- [x] 4.1 Credential opt-in and auth-model rows in README
- [x] 4.2 `hetzner-infra` in the statusline-tag list
- [x] 4.3 Threat-model "Exposed" mention of `HCLOUD_TOKEN`
- [x] 4.4 "Hetzner Cloud infrastructure (`--hetzner-infra`)" section with one-time setup
- [ ] 4.5 Help text and README mention the `ops_` prefix check added in a4dcd30 (not done)

## 5. Validation

- [ ] 5.1 `openspec validate add-hetzner-infra-support --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--hetzner-infra`
