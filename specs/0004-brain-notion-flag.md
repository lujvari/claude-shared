# 0004 — Notion mirror credentials for the Brain box

**Status:** draft

## Purpose

Brain (laslo/brain) mirrors part of its backlog to Notion; its spec/plan 0009 step 2 is a live probe against a scratch Notion database. The Brain box has no Notion credential, so the probe cannot run there. This adds a per-run opt-in that forwards the integration token and the scratch database id, in the same shape as the other credential flags, and turns it on in the Brain launcher.

## Requirements

- REQ-1: `run.sh --brain-notion` SHALL forward `BRAIN_NOTION_TOKEN` into the box from the launching environment when set, else from `op read` of `CLAUDE_DOCKER_BRAIN_NOTION_OP_REF`, defaulted to a reference in the vault the launcher's 1Password account already reads; an explicitly empty reference SHALL switch the 1Password path off.
- REQ-2: `--brain-notion` SHALL forward `BRAIN_NOTION_TEST_DATABASE_ID` from the launching environment, including the claude-docker env file; it is not a secret and has no 1Password path.
- REQ-3: A `--brain-notion` launch SHALL abort before `docker run`, naming the flag and the missing variable and never printing a value, when either variable is still empty after both sources.
- REQ-4: `--brain-notion` SHALL add `brain-notion` to `CLAUDE_DOCKER_FLAGS`; without the flag neither variable reaches the box.
- REQ-5: `cd-brain` SHALL launch with `--brain-notion`.

## Scenarios

### Scenario: Token from 1Password, id from the env file
- **Given** `BRAIN_NOTION_TOKEN` unset, the default op-ref readable, and `BRAIN_NOTION_TEST_DATABASE_ID` in the env file
- **When** the owner launches `cd-brain`
- **Then** the box has both variables and `brain-notion` in `CLAUDE_DOCKER_FLAGS`

### Scenario: Missing database id
- **Given** `--brain-notion` and no `BRAIN_NOTION_TEST_DATABASE_ID` anywhere
- **When** `run.sh` starts
- **Then** it exits non-zero before `docker run`, naming `--brain-notion` and `BRAIN_NOTION_TEST_DATABASE_ID`

### Scenario: No flag
- **Given** both variables set on the host
- **When** `run.sh` starts a box without `--brain-notion`
- **Then** neither variable is in the box

## Constraints

- The launcher's 1Password account is not granted the `brain` vault (it holds Brain's database password and tunnel token); the token item is copied into the vault that account reads, as `brain-cf-access` is.

## Out of scope

- Brain's own Notion mirror code and the probe itself (laslo/brain 0009).
- An identity probe of the token at launch (`lib/token-probe.sh`); Notion's `GET /v1/users/me` would serve if one is wanted later.
