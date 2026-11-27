# Plan 0005 — cd-kits launcher

**Spec:** specs/0005-cd-kits-launcher.md
**Effort:** simple
**Status:** done

## Changes

- `claude-docker/launchers/cd-kits` — new, from the README "Adding one" template.
- `claude-docker/launchers/cd-tools` — header: kit work routes to cd-kits; shared checkout.
- `claude-docker/launchers/cd-up` — `q1=(apg asr kits)`.
- `claude-docker/launchers/README.md` — q1 list; shared-checkout paragraph names cd-tools/cd-kits.

## Acceptance Checklist

- [x] REQ-1: `bash -n cd-kits`; with `CD_RUN` stubbed to echo its args, `cd-kits` prints `--claude-auth --gh <dev>/laslo/kits` and nothing else — verified: stub printed `--claude-auth --gh <scratch dev>/laslo/kits -- --continue`.
- [x] REQ-2: `grep` shows the routing and commit-by-path note in cd-tools and README — verified: cd-tools header and README shared-checkout paragraph.
- [x] REQ-3: `bash -n cd-up`; `q1` lists `kits` — verified: `q1=(apg asr kits)`, syntax ok; tabs open as `cd-$b`. Live `cd-up` run is the host's, after linking.
