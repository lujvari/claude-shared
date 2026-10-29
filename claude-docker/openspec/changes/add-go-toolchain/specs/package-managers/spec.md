## ADDED Requirements

### Requirement: Go toolchain pinned and on the default PATH

The image SHALL ship a Go toolchain at `/usr/local/go`, pinned by a Dockerfile `GO_VERSION` `ARG` and verified against per-architecture `GO_SHA256_X86_64` / `GO_SHA256_AARCH64` `ARG`s with `sha256sum -c` before extraction. `/usr/local/go/bin` and `/home/claude/go/bin` SHALL be on PATH through Dockerfile `ENV`, so that non-interactive shells that do not source `~/.bashrc` find `go` and `go install`ed tools. The image SHALL set `GOPATH=/home/claude/go`, inside the `claude-code-root` volume.

#### Scenario: go on PATH in Claude's Bash tool

- **WHEN** a box launches and Claude's Bash tool runs `go version`
- **THEN** it prints the pinned `GO_VERSION`
- **AND** `go env GOROOT` prints `/usr/local/go`

#### Scenario: go-installed tools persist and resolve

- **GIVEN** `staticcheck` was installed with `go install` in an earlier non-ephemeral box
- **WHEN** a new box's Bash tool runs `staticcheck -version`
- **THEN** it resolves from `/home/claude/go/bin` without any shell rc

#### Scenario: build fails on tampered Go tarball

- **GIVEN** a Go tarball that does not match the pinned `GO_SHA256_*` for the build architecture
- **WHEN** the Dockerfile runs `sha256sum -c`
- **THEN** the build fails before extraction and nothing is installed into `/usr/local/go`

### Requirement: Go runtime code-fetch documented in threat model

The README threat model's runtime code-fetch bullet SHALL list `go install`, `go run <module>@<version>` and Go toolchain auto-download (`GOTOOLCHAIN=auto`, triggered by a workspace `go.mod` `toolchain` line) as primitives that fetch and execute code chosen by the workspace at runtime.

#### Scenario: README names the Go fetch primitives

- **WHEN** a reader inspects `claude-docker/README.md` § Threat model
- **THEN** the runtime code-fetch bullet names `go install`, `go run`, and `GOTOOLCHAIN` auto-download
