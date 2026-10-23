## Why

`add-credential-fail-closed` stops a launch when a credential flag injects
*nothing*. It cannot see a token that is present but dead. Of the first ten
box-to-host agent-bus messages, three were exactly that: an expired or revoked
ADO PAT, SBP GitLab token and Supabase PAT. Each box got as far as its first
API call, stalled mid-task, and waited until a host session noticed and the
owner rotated the token. A launch-time check turns that into one line on the
terminal before the session starts, while the owner is still looking.

## What Changes

- **One identity probe per credential flag set on this launch.** After the
  fail-closed gate passes and before `docker run`, `run.sh` makes one cheap
  authenticated GET per flag to that service's whoami-style endpoint (see
  `design.md` for the table). The probes run in parallel, with a 1 s connect
  timeout and a 2 s total timeout each.
- **Warn, never block.** A rejected token (the service's "bad credential"
  answer: HTTP 401, or 403 for Cloudflare only) prints one stderr line:
  `claude-docker: --<flag> token rejected (HTTP 401) - rotate it on the host before relying on this box`.
  The launch continues.
- **Visible for the whole session.** Claude Code repaints the terminal as the
  container starts, so the stderr line alone goes unread. The rejected flags
  are also passed in as `CLAUDE_DOCKER_REJECTED_TOKENS` (e.g. `glab,ado`), and
  the statusline wrapper shows them as a red `token-dead:<flags>` tag next to
  the `docker:<flags>` one.
- **Quiet when the answer is unknown.** Network errors, timeouts, 5xx and any
  other unexpected status print nothing, so offline launches stay fast and
  silent.
- **Tokens stay out of argv and output.** Every probe feeds its auth header to
  `curl` as a config on stdin (`curl -K -`), never as `-H` on the command line,
  and prints only the flag and status code.
- **Opt-out.** `CLAUDE_DOCKER_NO_TOKEN_PROBE=1` skips every probe. A host
  without `curl` skips them too, silently.
- **Skipped flags:** `--aws`, `--tofu`, `--mepdb`, `--rr-e2e`, and `--tfe` when
  its token comes only from the mounted credentials file. Also `--ado` /
  `--ado-admin` when no organisation is known. See `design.md`.
- The probe logic lives in `lib/token-probe.sh`, sourced by `run.sh`, so a test
  can drive it with a stub `curl`.

## Impact

- `run.sh`: one source line and one call before `docker run`, the
  `CLAUDE_DOCKER_REJECTED_TOKENS` env, the red tag in the statusline wrapper;
  `print_help` documents `CLAUDE_DOCKER_NO_TOKEN_PROBE` and
  `CLAUDE_DOCKER_ADO_ORG`.
- `cd-ct`, `cd-ws13`: export `CLAUDE_DOCKER_ADO_ORG`.
- New `lib/token-probe.sh` and `lib/test_token_probe.py`.
- README credential section: one paragraph.
- Launch time: one round trip, about 0.3–0.6 s on a normal connection. Worst
  case is 2 s more, on a network that silently drops packets.
