## Why

Boxes that run with permission prompts on still stop for lookups the owner
approves every time. Probing a box in default mode showed that Claude Code
already runs plain read-only commands inside the workspace without asking
(`head`, `grep`, `sed -n`, `find`, `wc`, pipes of those), as its docs say.
What still prompts is reading the box's own config outside the workspace:
installed skills, inat user rules and the user `CLAUDE.md`. Those are the
lookups to allow.

## What Changes

- **`examples/settings.docker.json` gains `permissions.allow`** with three
  read rules: `Read(~/.claude/skills/**)`, `Read(~/.inat/rules/**)`,
  `Read(~/.claude/CLAUDE.md)`. Claude Code applies `Read` rules to the Read
  tool and to the paths of read-only Bash commands, so `head` or `ls` there
  stop prompting too.
- **Deny rules keep winning.** The existing `permissions.deny` list and the
  `deny-secret-reads.py` hook are unchanged, and a deny beats an allow, also
  for a path under an allowed directory.
- **Docs**: the README's seed paragraph names the allow list and why it is
  this short.

Not included:

- **agent-bus `inbox` / `status` rules.** Bash rules match the literal command
  text, and the agent-bus skill calls the script through a variable
  (`python3 $B inbox`), so such rules would rarely fire. `inbox --show` also
  writes a seen marker, so it isn't strictly read-only.
- **`permissions.additionalDirectories`** for the same paths: it also stops
  the prompts, but widens the working set rather than granting reads only.

Where the allowed paths come from: each is a read-only mount from the host
when the host has it (`run.sh` mounts skills, `CLAUDE.md` and inat rules only
if present). Otherwise the path sits on the shared home volume, and reading it
grants nothing a box couldn't already write there. None of the allowed
locations holds a credential today; skills copied with `cp -RL` should be
re-checked if host skills start symlinking outside their own directory.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `host-config-parity`: the example container settings allow reading the
  box's own skills, inat rules and user rules without a prompt.

## Impact

- **Code**: `claude-docker/examples/settings.docker.json`.
- **Docs**: `claude-docker/README.md`.
- **Specs**: delta to `host-config-parity`.
- **Host**: the live seed is the host's own `~/.claude/settings.docker.json`,
  which a box sees read-only. The control session merges the same three rules
  into its `permissions.allow` (it already holds other entries); boxes pick
  them up on their next start.
- No effect on `--yolo` or bypass-mode boxes, which never prompt.
