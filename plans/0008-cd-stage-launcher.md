# Plan 0008 — cd-stage launcher

**Spec:** specs/0008-cd-stage-launcher.md
**Effort:** simple
**Status:** approved

## Changes

- `claude-docker/launchers/cd-stage` — new; two `cd_workspace` calls like `cd-tools` (precedent), plus a `--stage` guard over the arguments before `--` (new pattern: no launcher has refused a run.sh flag before; the reason is spec Decisions).
- `claude-docker/launchers/cd-tools` — header: stage-broker work routes to cd-stage; shared checkout.
- `claude-docker/launchers/README.md` — shared-checkout paragraph names cd-tools/cd-stage.
- `specs/CURRENT.md` — one line for cd-stage.
- `OPEN.md` — parked cd-stage item replaced by: link-and-launch check, broker state split (first job), CT stack item routed to cd-stage.

## Acceptance Checklist

- [ ] REQ-1: `bash -n cd-stage`; with a scratch dev root holding a copy of the launchers and a `run.sh` stub that echoes its args, `cd-stage -- --continue` prints `--claude-auth --gh <dev>/tools/stage-broker <dev>/tools/claude-shared -- --continue`; `box_key` in `run.sh` turns the first workspace into `tools.stage-broker` (read at run.sh:573). Live: after the host links it, in the box `pwd` is `/workspaces/stage-broker`, `echo $AGENT_BUS_SELF` is `tools.stage-broker`, and `touch /workspaces/claude-shared/claude-docker/x` fails with EROFS. — stub half verified: printed `--claude-auth --gh <dev>/tools/stage-broker <dev>/tools/claude-shared -- --continue`; live half open (OPEN.md).
- [x] REQ-2: same stub: `cd-stage --stage ct` and `cd-stage --stage=ct` exit 1 with the reason and print no run.sh args; `cd-stage -- --stage` (a claude arg after `--`) is not refused. — verified: both refused with rc=1 and no ARGS line; `-- --stage` passed through.
- [x] REQ-3: `grep` shows the routing and commit-by-path note in cd-tools and README. — verified: cd-tools header and README cd-stage paragraph.
