# 0001 — Replace OpenSpec with numbered specs and plans

**Status:** approved

## Purpose

claude-docker tracks behavior and changes in OpenSpec only because it was forked from a repo that did. The owner's own workflow is numbered specs and plans, a single current-behavior document and an open-items list. Running both means two places to look and two formats to keep valid. This change moves claude-docker's own records onto the owner's workflow. The box image keeps bundling the OpenSpec CLI, which other projects still use.

## Requirements

- REQ-1: The repo SHALL hold one current-behavior document stating what claude-docker does today, one present-tense line per behavior, grouped under a fixed set of capability headings.
- REQ-2: The current-behavior document SHALL cover every behavior described by the OpenSpec base specs and by the requirements of unarchived OpenSpec changes whose code has shipped. A requirement that a later change rewrote SHALL appear only in its latest form.
- REQ-3: Where an OpenSpec text and the shipped code disagree, the current-behavior document SHALL describe the code.
- REQ-4: The repo SHALL hold a committed open-items list with one item per unarchived OpenSpec change that still had open verification steps. Each item SHALL name every open step with where to run it, what to run and what counts as a pass. OpenSpec bookkeeping steps (validate, archive) SHALL NOT be carried over.
- REQ-5: The stage broker SHALL be kept as a numbered spec in draft state with all of its requirements and scenarios, plus a draft plan that records what is already built and what remains.
- REQ-6: The repo SHALL NOT contain an OpenSpec directory, and no file SHALL cite an OpenSpec change folder or spec path. Mentions of the bundled OpenSpec CLI as a tool are allowed.
- REQ-7: Code comments that cited an OpenSpec change SHALL either be removed or cite something that exists in the repo.
- REQ-8: The box image SHALL keep bundling the OpenSpec CLI.

## Scenarios

### Scenario: Looking up current behavior
- **Given** the migration has landed
- **When** someone asks what `--sonar` does
- **Then** the current-behavior document has a line describing it, citing 0001

### Scenario: A rewritten requirement appears once
- **Given** four OpenSpec changes each rewrote the credentials opt-in requirement
- **When** the migration has landed
- **Then** the current-behavior document states the credentials opt-in behavior once, as the code does it today

### Scenario: Stale OpenSpec text is not carried over
- **Given** an OpenSpec requirement still says host `AWS_*` variables are forwarded into the box, while the launcher now writes a credentials file instead
- **When** the migration has landed
- **Then** the current-behavior document describes the credentials file

### Scenario: An open live check survives
- **Given** an OpenSpec change had an unticked live check (for example the cd-inat `gh api user` check)
- **When** the migration has landed
- **Then** the open-items list has that check with where, what and pass, runnable by a cold session without git history

### Scenario: The stage broker is still on the books
- **Given** the stage broker's core was built but its launcher integration and pilot were not
- **When** the migration has landed
- **Then** a draft numbered spec carries its seven requirements, and a draft plan lists the built parts and the remaining steps

### Scenario: No dangling OpenSpec references
- **Given** the migration has landed
- **When** the repo is searched for OpenSpec paths and change-folder citations
- **Then** nothing is found outside this spec and its plan

### Scenario: Comments lead somewhere real
- **Given** a comment in the launcher, Dockerfile or entrypoint used to cite an OpenSpec change folder
- **When** the migration has landed
- **Then** the comment cites nothing, or cites a file that exists in the repo

### Scenario: Other projects keep the CLI
- **Given** a box built from the image after the migration
- **When** it runs `openspec --version`
- **Then** the CLI answers as before

## Constraints

- Nothing may be lost outright: dropped OpenSpec text stays reachable through git history at the commit before deletion.
