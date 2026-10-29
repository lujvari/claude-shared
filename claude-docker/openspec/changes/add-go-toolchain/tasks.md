## 1. Image

- [x] 1.1 Add `GO_VERSION=1.27.3`, `GO_SHA256_X86_64`, `GO_SHA256_AARCH64` ARGs (hashes from `https://go.dev/dl/?mode=json`), next to the other pinned ARGs
- [x] 1.2 Add a `RUN` block after the .NET block: map `uname -m` to `amd64`/`arm64`, download `go${GO_VERSION}.linux-<arch>.tar.gz`, `sha256sum -c`, extract to `/usr/local`
- [x] 1.3 `ENV GOPATH=/home/claude/go PATH=/usr/local/go/bin:/home/claude/go/bin:${PATH}`, with a comment saying why it is `ENV` and not `.bashrc`
- [x] 1.4 Prove before the rebuild: run the download and `sha256sum -c` steps of the RUN block in a scratch dir for amd64 (pass) and with one hash byte flipped (fail)

## 2. Retire the hand install

- [ ] 2.1 Delete the two Go lines (`GOROOT`, Go PATH) from `~/.bashrc` in the `claude-code-root` volume
- [ ] 2.2 After the rebuilt image is verified, `rm -rf ~/go-toolchain` in the volume

## 3. Docs and spec

- [x] 3.1 README: add `go` to the bundled-CLIs line; add the Go fetch primitives to the threat model's runtime code-fetch bullet
- [x] 3.2 Amend the Purpose of `openspec/specs/package-managers/spec.md`: Go joins Flutter and .NET as base-image runtimes
- [x] 3.3 `openspec validate add-go-toolchain --strict`

## 4. Verify on the rebuilt image (host)

- [ ] 4.1 Host rebuild of `claude-code:local`
- [ ] 4.2 In a new box, from the Bash tool: `go version` prints 1.27.3, `go env GOROOT` prints `/usr/local/go`, `staticcheck -version` resolves
- [ ] 4.3 In cd-inat: an agent commit passes the pre-commit hook (go vet / staticcheck / go test)
- [ ] 4.4 Reply to bus msg 2bb134 with the commits and "rebuild needed", then `done` it
