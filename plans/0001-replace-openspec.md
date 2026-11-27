# Plan 0001 — Replace OpenSpec with numbered specs and plans

**Spec:** specs/0001-replace-openspec.md
**Effort:** big
**Status:** done

## Approach

Everything new lands at the repo root (`specs/`, `plans/`, `OPEN.md`), next to `CLAUDE.md` and `.claude/skills`, where the spec, plan and rigor skills look. OpenSpec history gets no numbers. Every folded behavior cites `(0001)`. The OpenSpec text stays readable after deletion with `git show <base>:claude-docker/openspec/...`, where `<base>` is the run's base commit.

Decisions settled with the owner on 2026-11-27:
- Files live at the repo root.
- Behavior is folded into `specs/CURRENT.md` with no verbatim copy kept.
- Stage-broker becomes spec 0002 plus a draft plan 0002.
- Open checks go to a committed root `OPEN.md`.
- The image keeps the OpenSpec CLI, because ai-transcribe still uses it.

How the fold works. Source is about 1,100 lines of base specs plus 1,750 lines of unarchived change deltas, checked against `run.sh` (2,006 lines), `entrypoint.sh`, `lib/`, `launchers/`, `hooks/` and `Dockerfile`. It is split into two tasks by capability.
- **Merge rule:** a MODIFIED delta replaces the base text of that requirement. When several changes modify one requirement (Credentials opt-in: aws-op-fallback, jira, tfe, tofuenv; braindb-support then braindb-compose-network; git-insteadof then use-git-credential-helper), the code decides the final wording, never the delta order.
- **Shipped means** the behavior is present in the code; a requirement whose code is absent is left out (e.g. cd-up `--home` placements: `launchers/cd-up` has only `work/*` rectangles).
- **Paths:** OpenSpec `/root/...` paths are written as `/home/claude/...`.
- `changes/add-claude-docker-help` duplicates the base `cli-help` spec and is folded once.
- Each deviation from OpenSpec text (REQ-3) is logged by the implementer as an Assumption in the run file, with source and code `file:line`. Before the closeout commit, review-run copies them into that commit's message so git keeps them.

The fixed `CURRENT.md` headings, with the floor of behavior lines under each (the distinct requirement names across base specs and unarchived changes):

| Heading | Source capabilities | Floor |
|---|---|---|
| `## External CLIs and credentials` | external-cli-tools | 27 |
| `## CLI help` | cli-help | 4 |
| `## Container network` | container-network | 1 |
| `## Container user` | container-user | 2 |
| `## Host config parity` | host-config-parity | 7 |
| `## Launchers` | launchers | 5 |
| `## Workspace mounts` | multi-workspace-mounts | 11 |
| `## Bundled tools and package managers` | package-managers, openspec-cli | 12 |
| `## Session storage` | persistent-session-storage | 3 |
| `## Session worklog` | session-worklog | 5 |

`.claude/runs/drop-openspec-1.check-current.py` (local, never committed) checks the headings, the floors and that every bullet ends in `(0001)`.

## Changes

- `specs/0002-stage-broker.md` — new, Status `draft`. Spec format only: R1–R7 of `changes/add-stage-broker/specs/stage-broker/spec.md` become REQ-1..7, scenarios kept, no paths or implementation (spec SKILL rules).
- `plans/0002-stage-broker.md` — new, Status `draft`, `**Spec:** specs/0002-stage-broker.md`. The Approach holds the design (`design.md`, `proposal.md`) and what is built: tasks 0.x–2.2, the broker core in the dev-root `tools/stage-broker/`, 72 tests. The Acceptance Checklist holds the remaining tasks 3.1–4.3, each starting with the REQ ids it covers.
- `specs/CURRENT.md` — new; the table above.
- `OPEN.md` — new.
  - One item per unarchived change with unticked tasks at `<base>`: 23 changes, minus add-git-insteadof (dropped: its open task is only archive order) and add-stage-broker (moves to plan 0002), so 21 items.
  - Shape per the open-items skill: `- **<change topic>** — <what is open>. Next: <steps>`. Every open step is listed with where / what / pass.
  - Validate and archive steps are dropped: tools-rw-flag 5.1, use-git-credential-helper 5.3. aws-op-fallback 6.1 is kept as its decision only.
  - Stale `/root` paths become `/home/claude` (tofuenv 3.x). Steps with no pass bar get one from the code: braindb 3.2 gets "N consecutive runs with no connect timeout in the suite log". cd-up 4.2/4.4 name the PowerShell working-area query inline (`Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens | % WorkingArea`).
- `claude-docker/Dockerfile` — comments at lines 5, 79-80 and 532 lose their OpenSpec folder citations: reworded to stand alone, or pointing at `specs/CURRENT.md`. The OpenSpec CLI install at lines 22, 208 and 222 stays.
- `claude-docker/README.md` — line 461 drops the pointer to the token-probe design table; the line already names the endpoints. Line 738 points at `../specs/CURRENT.md`, `../specs/` and `../plans/`. Lines 5 and 572 (CLI mentions) stay.
- `claude-docker/entrypoint.sh` lines 6-7, `claude-docker/lib/{gh-profile,ado-profile,token-probe}.sh` line 2 — drop the change citations.
- `lychee.toml` line 12 — drop the `openspec/changes/archive` exclude.
- `openspec/` at the repo root (upstream's add-ci-tests change, 5 files) and `skills/spec/` (upstream's OpenSpec-format skill and its examples), deleted. The owner has cut ties with the upstream fork (2026-11-27); `skills/.gitkeep`, `agents/` and `.github/` stay. `.github/scripts/check-frontmatter.py` globs `skills/*/SKILL.md` and still passes with no matches.
- `claude-docker/openspec/` — deleted, last.

After the run, done attended in the main session (not run tasks: the files sit outside the run worktrees):
- Fold the 13-line, gitignored `.claude/OPEN.md` into the root `OPEN.md`, drop its OpenSpec items, and delete it.
- In `kits/plans/0005-clipboard-relay.md:33`, repoint the add-stage-broker design citation at `claude-shared/plans/0002-stage-broker.md`.

## Acceptance Checklist

- [x] REQ-1, REQ-2: `python3 .claude/runs/drop-openspec-1.check-current.py specs/CURRENT.md` exits 0 (headings, floors, `(0001)` on every bullet). Then a reviewer samples 5 base requirements and 5 change requirements and finds each covered. — verified: check-current.py exits 0 at review; owner sampled 5+5 requirements (manual test 1)
- [x] REQ-3: each deviation Assumption in the run file names source and code `file:line`; the reviewer re-checks 3 against the code. They are copied into the closeout commit message. — verified: 29 deviation Assumptions (A4–A32) each cite file:line; owner re-checked 3 (manual test 2); copied into this closeout commit
- [x] REQ-4: `OPEN.md` has 21 `- **` items. `grep -ci openspec OPEN.md` and `grep -c '/root' OPEN.md` are both 0. The reviewer runs one item cold and finds it complete. — verified: 21 items, both greps 0 at review; owner ran one item cold (manual test 3)
- [x] REQ-5: `specs/0002-stage-broker.md` has 7 `- REQ-` lines and Status draft. `plans/0002-stage-broker.md` has Status draft. `spec-check.py 0002` reports no `[pairing]` finding. — verified: run T1 Verify passed and re-passed at review
- [x] REQ-6: `test ! -e claude-docker/openspec && test ! -e openspec && test ! -e skills/spec`. `git grep -nE 'openspec/|openspec:|openspec change|changes/(archive|add-)'` hits only `specs/0001-*` and `plans/0001-*`. — verified: dirs absent; git grep hits only plans/0001-replace-openspec.md at review
- [x] REQ-7: `bash -n claude-docker/entrypoint.sh claude-docker/lib/*.sh` passes. Every path cited in a changed comment exists (`git diff <base> -U0` reviewed). — verified: bash -n passes; every changed comment cites specs/CURRENT.md, which exists
- [x] REQ-8: `grep -c '@fission-ai/openspec' claude-docker/Dockerfile` is 1. — verified: count is 1 at review
