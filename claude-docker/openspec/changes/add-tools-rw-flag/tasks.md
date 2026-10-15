## 1. run.sh

- [x] 1.1 Initialize `WITH_TOOLS_RW=0`; add `--tools) WITH_TOOLS_RW=1 ;;` to the case statement
- [x] 1.2 Add `--tools` to the help heredoc
- [x] 1.3 For each workspace that strictly contains `SELF_DIR`, add `-v "$SELF_DIR:/workspaces/<name><sub>:ro"`
- [x] 1.4 Skip the overlay under `--ro` and under `--tools`
- [x] 1.5 Narrow the overlay from the workspace's top-level `tools/` to the launcher's own directory (b95c7fa)

## 2. entrypoint.sh

- [x] 2.1 No changes.

## 3. Smoke tests

Not run as part of this retroactive record; the 210c557 and b95c7fa commit messages record no verification.

- [ ] 3.1 Mounting the dev root: writing under the launcher directory inside the container fails; writing elsewhere under `tools/` succeeds
- [ ] 3.2 Same mount with `--tools`: writing under the launcher directory succeeds
- [ ] 3.3 Mounting the launcher directory itself: it is writable without `--tools`

## 4. Documentation

- [x] 4.1 README flag row for `--tools`
- [x] 4.2 README threat model mentions the overlay

## 5. Validation

- [ ] 5.1 `openspec validate add-tools-rw-flag --strict` exits 0 (not run)
- [x] 5.2 `claude-docker --help` shows `--tools`
