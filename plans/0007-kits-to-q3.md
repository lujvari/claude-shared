# Plan 0007 — cd-kits opens in the Q3 window

**Spec:** specs/0007-kits-to-q3.md
**Effort:** simple
**Status:** done

## Changes

- `claude-docker/launchers/cd-up` — `q1=(apg asr)`, `q3=(tools dev mep kits)`.
- `claude-docker/launchers/README.md` — window group list.
- `specs/CURRENT.md` — the cd-up groups line and the cd-kits line.

## Acceptance Checklist

- [x] REQ-1: `bash -n cd-up`; `window_of kits` prints `q3`.
- [x] REQ-2: `grep` for the groups in README and CURRENT.md matches cd-up.
