## Why

Go reaches boxes today only as a hand install in the shared `claude-code-root`
volume (`~/go-toolchain`, go1.25.10, with `staticcheck` in `~/go/bin`), put on
PATH by `~/.bashrc`. Claude's Bash tool does not pick up those PATH lines, so
`go` is missing from the tool shell even though `GOROOT` is set. In the
sbp.ai.inat box this fails the pre-commit hook (`go vet`, `staticcheck`,
`go test`) on every agent commit. Nothing reproduces the hand install, and
`--ephemeral` boxes have no Go at all.

The `package-managers` spec reserves language runtimes like Go for child images.
The owner chose to put Go in the base image anyway, alongside the Flutter and
.NET exceptions that already live there, rather than add the first child image.

## What Changes

- **Install Go in the image**: pinned `GO_VERSION` (1.27.3) with per-arch
  `GO_SHA256_*` ARGs, verified with `sha256sum -c` before extraction into
  `/usr/local/go`. Same pin-and-verify pattern as `uv` and .NET.
- **Put Go on the default PATH with `ENV`**, not `.bashrc`:
  `/usr/local/go/bin` and `$GOPATH/bin` (`GOPATH=/home/claude/go`, in the
  persistent volume, so `go install`ed tools like `staticcheck` survive and stay
  on PATH). No `ENV GOROOT`: the `go` binary derives it.
- **Retire the hand install**: delete the two Go lines from the volume's
  `~/.bashrc`. Its `GOROOT=/root/go-toolchain/go` would otherwise point the
  image's `go` at the old 1.25 tree. `~/go-toolchain` can then be deleted.
- **Amend the `package-managers` Purpose** to name Go as a base-image runtime,
  with Flutter and .NET.
- **README**: add `go` to the bundled-CLIs line, and add `go install`/`go run`
  and toolchain auto-download (`GOTOOLCHAIN=auto`) to the runtime code-fetch
  bullet in the threat model.

## Out of scope

- Baking `staticcheck` (or other Go tools) into the image. It stays a volume
  install in `~/go/bin`, so `--ephemeral` boxes lack it.
- The glab default-host half of the same host request; `92e30ae` already
  covers it.

## Impact

- Image rebuild required; the image grows by about 250 MB.
- Every box gets `go` on PATH, Bash tool included.
