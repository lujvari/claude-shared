## Context

By the time the fail-closed gate in `run.sh` has passed, every credential flag
on the launch has its token in a host env var (`GH_TOKEN`, `GITLAB_TOKEN`, …),
from the host env or an `op read`. Nothing checks that the service still
accepts it. The probe runs at that point, on the host, before `docker run`.

## Goals / Non-Goals

**Goals:**
- Name a dead token at launch, in one line, for each flag whose service has a
  cheap identity endpoint.
- Add no noise and at most 2 s when offline, and no visible delay normally.

**Non-Goals:**
- Blocking the launch. A false alarm must never cost a session.
- Checking scopes or permissions. Only "is this token accepted at all".
- Probing from inside the container, or re-probing during a session.

## Decisions

### 1. Endpoints

| Flag | Request | "Rejected" means |
|---|---|---|
| `--gh` | `GET https://api.github.com/user`, `Authorization: Bearer $GH_TOKEN` (or `GITHUB_TOKEN`) | 401 |
| `--glab` | `GET https://<host>/api/v4/user`, `PRIVATE-TOKEN`, for each host in `$glab_hosts` (default `gitlab.com`) | 401 on **every** host |
| `--ado` | `GET https://dev.azure.com/<org>/_apis/connectionData`, Basic `:$AZURE_DEVOPS_EXT_PAT` | 401 |
| `--ado-admin` | same, with `AZURE_DEVOPS_ADMIN_PAT` | 401 |
| `--jira` | `GET $JIRA_BASE_URL/rest/api/3/myself`, Basic `$JIRA_USER_EMAIL:$JIRA_API_TOKEN` | 401 |
| `--supabase` | `GET https://api.supabase.com/v1/projects`, Bearer | 401 |
| `--cloudflare` | `GET https://api.cloudflare.com/client/v4/user/tokens/verify`, Bearer; if that rejects and `CLOUDFLARE_ACCOUNT_ID` is set, also `…/accounts/<id>/tokens/verify` | 401/403 on both |
| `--openrouter` | `GET https://openrouter.ai/api/v1/key`, Bearer | 401 |
| `--sonar` | `GET ${SONAR_HOST_URL:-https://sonarcloud.io}/api/authentication/validate`, Bearer | 200 with `"valid":false` in the body, or 401 |
| `--tfe` | `GET https://app.terraform.io/api/v2/account/details`, Bearer `$TF_TOKEN_app_terraform_io` | 401 |
| `--hetzner-infra` | `GET https://api.hetzner.cloud/v1/locations?per_page=1`, Bearer `$HCLOUD_TOKEN` | 401 |

403 counts as rejected only where the service uses it for a bad token (the
Cloudflare row). Elsewhere 403 means "valid token, missing scope", which the
probe cannot tell from a resource ACL, so it stays quiet.

### 2. Skipped flags

- `--aws`: needs the AWS CLI and SSO cache on the host, and is slow. Not a
  cheap GET.
- `--tfe` with no `TF_TOKEN_app_terraform_io` (token only in the mounted
  `credentials.tfrc.json`), and `--tofu`: probing would mean parsing a
  credentials file on the host. Left out of this change.
- `--mepdb`: a Postgres URL, not HTTP.
- `--rr-e2e`: a test account password; checking it means a Supabase password
  grant, which counts as a login attempt.
- `--ado` / `--ado-admin` with no organisation. ADO has no org-less endpoint
  that accepts an org-scoped PAT: the profile API on `app.vssps.visualstudio.com`
  answers 401 for a valid PAT scoped to one organisation, which would be a
  false alarm. The org comes from `CLAUDE_DOCKER_ADO_ORG` (new, optional,
  non-secret), exported by each ADO launcher (`cd-ct`, `cd-ws13`) because the
  org is a property of the project. A launch without it skips the probe.

### 3. Timing

Every probe is a background `curl --connect-timeout 1 --max-time 2`; `run.sh`
waits for all of them. Normal cost is one round trip to the slowest service.
On a network that silently drops packets the cost is 2 s, which is accepted:
cutting it shorter would turn slow-but-working links into silent misses.

### 4. Keeping tokens out of argv and output

Each probe writes a curl config to curl's stdin:

```text
url = "https://api.github.com/user"
header = "Authorization: Bearer <token>"
```

`argv` holds only `-K - -s -o <tmpfile> -w %{http_code}` and the timeouts, so
`ps` on the host never shows a token. The response body goes to a temp file
under a `mktemp -d` dir (mode 700), read only by the Sonar check, and removed
on exit. A token containing `"` or `\` is escaped for the config syntax. Output
names the flag and the status code, nothing else.

### 5. Where the result shows

The stderr line is printed, but Claude Code repaints the terminal the moment
the container starts; the `add-credential-fail-closed` change aborts instead of
warning for that reason. Blocking is ruled out here, so the result is carried
into the session instead. `token_probe_all` leaves the rejected flags in
`TOKEN_PROBE_REJECTED` (comma-separated, no dashes). `run.sh` forwards that as
`CLAUDE_DOCKER_REJECTED_TOKENS`, and the existing statusline wrapper adds a red
`token-dead:<flags>` tag after the yellow `docker:<flags>` one. The tag needs
the host statusline script, like the `docker:` tag does.

Rejected alternative: pausing the launch a few seconds after a warning. The
line is then seen once, and the delay hits exactly the launches that already
have a problem.

### 6. Code shape

`lib/token-probe.sh` defines `token_probe_all`, which reads the `WITH_*` flags
and token variables already set in `run.sh`. `run.sh` sources it through
`$SELF_DIR` and calls it after the fail-closed gate. The statusline wrapper is
already staged by then; only the env var is added after the probe. The test drives the
function in a `bash` subprocess with a stub `curl` on `PATH` that returns
scripted codes and records its argv and stdin. The test then asserts the
warning lines, the quiet cases, the opt-out, and that no token ever appears in
argv.

## Risks / Trade-offs

- **False alarm on a valid token**: the risk is a service answering 401 for a
  scope problem. It is limited to services where 401 is documented as "bad or
  expired token", and the result is only a warning.
- **Endpoint drift**: a service may retire one of these endpoints. A 404 then
  silences the probe for that flag instead of breaking the launch.
- **Extra traffic**: one request per flag per launch, all to identity endpoints.
  Negligible against rate limits.
