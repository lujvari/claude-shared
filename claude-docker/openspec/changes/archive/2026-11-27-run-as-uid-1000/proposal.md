## Why

Boxes ran as root. On WSL, Docker Desktop's drvfs `metadata` mount records the
writer's uid, so every file a box created or rewrote under `/mnt/c` landed as
uid 0 / mode 0744. The WSL user (`aslojvari`, uid 1000) could then neither run
nor edit it. On 2026-10-23 that broke `cd-mep` (`run.sh: Permission denied`
after a box commit) and `cd-brain`; `laslo/brain` had 838 root-owned files.

## What Changes

- **Run as uid/gid 1000.** The image renames the base image's uid-1000 user
  to `claude` with `HOME=/home/claude` and ends with `USER claude`. `run.sh`
  passes `--user 1000:1000` explicitly.
- **Not widened.** `--cap-drop ALL` and `no-new-privileges` stay, and the
  `--cap-add DAC_OVERRIDE`/`FOWNER` pair is removed. The change adds no sudo,
  no setuid binaries, no root-then-drop entrypoint, no `--userns` and no
  `--privileged`. The mount set is unchanged and only re-pointed: `ro` stays
  `ro`, and `/bus` scoping is untouched.
- **Home layout.** `claude-code-root` mounts at `/home/claude` and
  `claude-code-home` at `/home/claude/.claude`. Every `/root/...` bind target
  moves to the same path under `/home/claude`. The tmpfs masks get
  `uid=1000,gid=1000,mode=0700`. The mountpoint parents (`.config/gh`,
  `.config/glab-cli`, `.aws`, `.terraform.d`, `.local/bin`, `.venvs`) are
  pre-created in the image with uid 1000 ownership, because runc creates
  missing ones as root.
- **`/root` symlink.** `/root` becomes a symlink to `/home/claude`. Absolute
  `/root/...` paths that earlier boxes recorded in the volumes, and hook
  commands in older `settings.docker.json` files, keep resolving.
- **Git credential helpers.** These move from `/etc/gitconfig`, which uid 1000
  can't write, to `/tmp/claude-docker-gitconfig`. `/etc/gitconfig` includes
  that file, so it keeps system precedence and is still discarded on exit.
- **Writable SDK trees.** `/opt/flutter`, `/opt/android-sdk`, `/opt/tfenv`
  and `/opt/tofuenv` are chowned to 1000 at build, since each tool writes
  inside its own tree.
- **Narrowed.** `apt-get` no longer works at runtime, and the
  `APT::Sandbox::User` workaround is removed. `npm install -g` goes to
  `~/.local` via `NPM_CONFIG_PREFIX`.
- **Entrypoint.** It fails with a pointer to the migration when `~/.local/bin`,
  `~/.claude` or `~/.aws` is not writable, instead of failing with a bare
  EACCES.
- **One-off migration.** The owner runs a throwaway root container to chown
  the two volumes, then a host-side `find -uid 0 -exec chown` over
  `/mnt/c/dev`. The README documents both. The box itself is never given the
  power to chown.

## Impact

- Files: `Dockerfile`, `entrypoint.sh`, `run.sh`, `README.md`,
  `examples/settings.docker.json`.
- Existing volumes must be migrated once before the first launch on the new
  image.
