## Why

`inat --user` (inat spec 0025 §8) installs contextual rules beside the user's
Claude config: the files go in `~/.inat/rules/<name>.md`, and each one gets a
pointer line in the inat-managed section of `~/.claude/CLAUDE.md`. Boxes
already get that `CLAUDE.md` read-only, but not the rules directory, so inside
a box every pointer leads to a missing file and the rule never loads.

## What Changes

- **Mount the rules directory read-only in every box.** The rules belong to
  the home whose `CLAUDE.md` points at them. `run.sh` therefore resolves
  `$CLAUDE_CONFIG_DIR` to its real path (following symlinks) and looks in its
  parent for `.inat/rules`. On the owner's WSL host, `~/.claude` lives on the
  Windows drive (this box's `CLAUDE.md` mount is 9p from `C:\`), so a
  `$HOME/.inat/rules` lookup would miss rules that a Windows-side `inat --user`
  wrote. If that directory exists, `run.sh` binds it read-only at
  `/home/claude/.inat/rules`, the path the `~/.inat/rules/<name>.md` pointers
  name literally. `--claude-dir` moves the rules lookup along with
  `CLAUDE.md`.
- **Only the rules directory.** The rest of the host's `.inat` (`config.json`,
  cache) is host state and stays off the box.
- **Silent when nothing is pointing; a warning when something is.** If the
  directory is absent and the mounted `CLAUDE.md` has no `~/.inat/rules/`
  pointer, `run.sh` mounts nothing and prints nothing. If the directory is
  absent and a pointer exists, `run.sh` prints one warning naming the path it
  looked in. Without that warning, a wrong guess about where inat writes would
  fail with no trace.
- **Direct `:ro` bind, not staged.** This matches `CLAUDE.md`, which is
  already a direct bind from the same home. The choice depends on the host
  directory holding no symlinks; that is checked on the real host before any
  code is written (tasks 0.1). Changes take effect on the next launch, as with
  `CLAUDE.md`. A running box may see an in-place edit sooner, but neither
  mount guarantees it.
- **The image pre-creates `/home/claude/.inat` and `/home/claude/.inat/rules`**
  owned by uid 1000, beside the other mountpoint parents in the Dockerfile.
  Otherwise runc creates the missing parent as root on a fresh volume or under
  `--ephemeral`, and in-box `inat` can no longer write `~/.inat/cache`. The
  README's one-off volume migration gets `.inat` in its `mkdir` list.
- **Applies under `--ro` and `--ephemeral`**: it is host config, not the
  workspace.
- **Docs**: a README row and a line in `--claude-dir` help.

Behaviour change inside a box: `~/.inat/rules` is read-only whenever the host
has rules, so an in-box `inat --user` fails there. That matches how
`~/.claude/CLAUDE.md` already behaves, since it is read-only too. User-scope
installs happen on the host.

Out of scope (deliberately):

- **Skills.** Host `~/.claude/skills` already reaches boxes (staged read-only
  over `/home/claude/.claude/skills`), so inat's second ask needs no change.
- **An opt-out flag.** The mount is read-only and holds only markdown.
- **Volumes created before this change** that already hold a root-owned
  `~/.inat`. None is known: this box's `~/.inat` is owned by `claude`. The
  README migration covers it if one turns up.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `host-config-parity`: adds a read-only mount of the host's inat user rules
  directory, located from the config dir's home.

## Impact

- **Code**: `claude-docker/run.sh` (one block beside the `CLAUDE.md` mount,
  plus the help line), `claude-docker/Dockerfile` (two `install -d` paths).
  The image needs a rebuild.
- **Docs**: `claude-docker/README.md` (table row, intro wording, migration
  `mkdir` list).
- **Specs**: delta to `host-config-parity`.
