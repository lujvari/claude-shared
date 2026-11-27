# Plan 0004 — Notion mirror credentials for the Brain box

**Spec:** specs/0004-brain-notion-flag.md
**Effort:** small
**Status:** draft

## Approach

Copy the `--braindb`/`--brain` shape in `run.sh`: a `WITH_BRAIN_NOTION` switch, both names in `ENV_VARS` (forwarded when set on the host or in the env file), a defaulted op-ref `CLAUDE_DOCKER_BRAIN_NOTION_OP_REF=op://claude-docker/brain-notion-token/credential` read only when `BRAIN_NOTION_TOKEN` is empty, an `op_needed` entry so the op preflight covers it, `brain-notion` in `DOCKER_FLAGS` right after `brain` (the README table order), and `cred_require --brain-notion BRAIN_NOTION_TOKEN` in the credential gate.

The database id is env only, like `CLOUDFLARE_ACCOUNT_ID`, but unlike it the flag is useless without one, so it is required. Not through `cred_require`: that gate's abort text blames 1Password reads and offers `CLAUDE_DOCKER_OP_OPTIONAL`, both wrong for a missing env-file line. A separate check right after the env file is loaded exits 1 with `--brain-notion needs BRAIN_NOTION_TEST_DATABASE_ID (not a secret): add it to <env file>`, before any `op` call. New pattern: no existing flag requires a non-secret env value.

Deviation from the host's request (`op://brain/...` for both): the run.sh rule for `--brain` says the launcher's service account reads `claude-docker` only and must never get `brain`, so the token default points at a `claude-docker` copy, and the id needs no 1Password item.

## Changes

- `claude-docker/run.sh` — help text, switch, flag case, `ENV_VARS`, op-ref default, `op_needed`, op read block, `DOCKER_FLAGS`, one `cred_require` line, the id check after the env-file loader.
- `claude-docker/launchers/cd-brain` — `--brain-notion` on the `cd_test_db_run` line; header comment.
- `claude-docker/README.md` — rows after `--brain` in both flag tables (:44-55 style and :120-135 style), `brain-notion` in the `CLAUDE_DOCKER_FLAGS` list (:106), `--brain-notion` in the "Not checked" probe list (:464); the `--mepdb` row's "one of three flags" with a default ref (:49), already stale, loses the count.
- `claude-docker/run.sh` help for `--mepdb` (:192-198), same count fix.
- `specs/CURRENT.md` — at closeout: bullets beside the `--brain` ones (:46-47), `--brain-notion` in the end-state list (:28) and the not-probed list (:61), and the `cd-brain` launch flag.

## Dependencies

The owner creates `brain-notion-token` (field `credential`) in vault `claude-docker` and adds `BRAIN_NOTION_TEST_DATABASE_ID=<id>` to `~/.config/claude-docker/env` in WSL.

## Acceptance Checklist

All of REQ-1 to REQ-4 run `run.sh` to `docker run` in a new `claude-docker/lib/test_brain_notion.py`, which no existing test does (`RunFlagTest` stops at argument checks). Each run gets a clean env built from scratch, not `os.environ` (precedent: `lib/test_gh_profile.py`): temp `HOME`, a temp workspace, `CLAUDE_DOCKER_ENV_FILE` at a temp file, `CLAUDE_DOCKER_BUS_DIR=""`, no `CLAUDE_DOCKER_BRAIN`, `OP_SERVICE_ACCOUNT_TOKEN` a dummy. Stub `op` on PATH: exits 0 on `whoami`, logs `read` refs and prints a fixed fake value. Stub `docker`: on `run`, logs argv plus the values of the `-e NAME` variables it was handed, and exits 0; other subcommands exit 0 quietly. If run.sh needs more before `docker run` than these stubs give, the test grows its stubs, never a run.sh test hook.

- [x] REQ-1: token unset: the stub `op` is asked for `op://claude-docker/brain-notion-token/credential` and the value reaches `docker run` as `-e BRAIN_NOTION_TOKEN`; `CLAUDE_DOCKER_BRAIN_NOTION_OP_REF=""` asks `op` nothing; a host token is used as is. — verified: `test_token_from_default_ref`, `test_empty_ref_switches_op_off`, `test_host_token_wins`.
- [x] REQ-2: an id in a scratch `CLAUDE_DOCKER_ENV_FILE` reaches `docker run` as `-e BRAIN_NOTION_TEST_DATABASE_ID`, and no op ref is read for it. — verified: `test_database_id_from_env_file`.
- [x] REQ-3: id missing: exit 1, stderr names `--brain-notion` and `BRAIN_NOTION_TEST_DATABASE_ID`, no `op read` and no `docker run`. Token missing (`op` read returns empty): exit 1 through the credential gate naming `--brain-notion`. Neither output contains the fake values. — verified: `test_missing_database_id_aborts_before_op`, `test_missing_token_aborts_in_credential_gate`.
- [x] REQ-4: with the flag `CLAUDE_DOCKER_FLAGS` contains `brain-notion`; without it, both set on the host, neither name is passed to `docker run`. — verified: `test_flag_listed`, `test_without_flag_nothing_forwarded`; 6 of the 8 tests fail against the previous run.sh.
- [ ] REQ-5: owner launches `cd-brain`; in the box `len=${#BRAIN_NOTION_TOKEN}` is non-zero and `BRAIN_NOTION_TEST_DATABASE_ID` is set.
- [x] Tests pass: `python3 -m unittest discover -s claude-docker/lib -p 'test_*.py'`. — verified: lib and hooks discover runs OK.
