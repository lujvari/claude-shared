# 0003 — Box tooling for .NET and SQL Server work

**Status:** done

## Purpose

A box working on a .NET and SQL Server project cannot query or deploy a database, build a repo whose worktrees use relative paths, or drive a browser from Python, so it cannot verify its own changes. These capabilities serve every box, not one project; the sbp.ct box is the first user. Bringing up the stack itself is spec 0002; private package feeds already work through a user-level config that references the box's Azure DevOps token.

## Requirements

- REQ-1: Every box SHALL offer, on the default PATH, a SQL Server command-line client that runs a query against a server reachable from the box.
- REQ-2: Every box SHALL offer, on the default PATH, a database deployment tool that publishes a compiled database package to a server reachable from the box.
- REQ-3: Every box that ships a browser SHALL let a Python script import the browser-automation module and drive that browser headless, with no browser download at run time.
- REQ-4: A .NET build in any box SHALL succeed in a repository whose git configuration enables relative worktree paths.

## Scenarios

### Scenario: Query a database
- **Given** a box and a SQL Server reachable from it
- **When** the box runs a query with the bundled client
- **Then** the result prints and the client exits 0

### Scenario: Publish a database package
- **Given** a box, a compiled database package and a SQL Server reachable from it
- **When** the box publishes the package to a new database
- **Then** the database exists with the package's schema

### Scenario: Python browser test
- **Given** a box with a bundled browser and no Playwright browsers downloaded
- **When** a Python script launches the bundled browser headless and loads a page
- **Then** the page loads and the script exits 0

### Scenario: Build in a relative-worktree repo
- **Given** a .NET repository checked out as a worktree with relative paths
- **When** the box builds it
- **Then** the build succeeds

## Constraints

- Every added tool is pinned to one version and checked against a known hash when the image is built, as the tools already bundled are.
- The browser-automation module's version matches the bundled browser's major version, and the two are bumped together.

## Open Questions

- Which architectures get the SQL client and deployment tool? Default: every architecture the image builds for that the vendor publishes.
