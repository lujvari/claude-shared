## 1. Probe library

- [x] 1.1 `lib/token-probe.sh`: `token_probe_all` launches one background probe per flag in the `design.md` table and waits for all of them
- [x] 1.2 Each probe passes url and auth header to `curl -K -` on stdin, with `--connect-timeout 1 --max-time 2`
- [x] 1.3 Rejected (per-row rule) → one stderr line naming the flag and status; anything else → silent
- [x] 1.4 GitLab warns only if every host in `$glab_hosts` rejects; Cloudflare falls back to the account verify endpoint; Sonar reads `"valid":false`
- [x] 1.5 `CLAUDE_DOCKER_NO_TOKEN_PROBE=1` or no `curl` on PATH → return immediately

## 2. run.sh

- [x] 2.1 Source `$SELF_DIR/lib/token-probe.sh`; call `token_probe_all` after the fail-closed gate, before `docker run`
- [x] 2.2 Read optional `CLAUDE_DOCKER_ADO_ORG` for the ADO probes; `cd-ct` and `cd-ws13` export it
- [x] 2.3 `print_help`: document `CLAUDE_DOCKER_NO_TOKEN_PROBE` and `CLAUDE_DOCKER_ADO_ORG`
- [x] 2.4 Forward `TOKEN_PROBE_REJECTED` as `CLAUDE_DOCKER_REJECTED_TOKENS`; statusline wrapper shows a red `token-dead:<flags>` tag

## 3. Tests

- [x] 3.1 `lib/test_token_probe.py` with a stub `curl`: 401 warns, 200 is quiet, curl exit 28 (timeout) is quiet, 5xx is quiet
- [x] 3.2 GitLab two-host case, Sonar `valid:false`, Cloudflare fallback
- [x] 3.3 Opt-out and no-curl return without calling curl
- [x] 3.4 No token value appears in any recorded curl argv or in stderr
- [x] 3.5 `TOKEN_PROBE_REJECTED` lists exactly the rejected flags

## 4. Documentation

- [x] 4.1 README credential section: what the probe does, the opt-out, the skipped flags
- [x] 4.2 Spec delta in `specs/external-cli-tools/spec.md`

## 5. Validation

- [x] 5.1 `bash -n run.sh lib/token-probe.sh`
- [x] 5.2 `python3 -m unittest lib/test_token_probe.py hooks/test_deny_secret_reads.py`
- [x] 5.3 `openspec validate add-token-probe --strict`
- [ ] 5.4 Owner: live launch with one deliberately bad token prints the warning and still starts
