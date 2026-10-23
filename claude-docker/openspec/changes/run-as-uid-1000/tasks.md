## 1. Image

- [x] 1.1 Rename uid 1000 to `claude`, HOME `/home/claude`; pre-create mountpoint parents owned by 1000; `/root` → symlink; `USER claude`
- [x] 1.2 chown `/opt/flutter`, `/opt/android-sdk`, `/opt/tfenv`, `/opt/tofuenv` to 1000 in their install layers
- [x] 1.3 PATH, `PUB_CACHE`, dotnet tools under `/home/claude`; `NPM_CONFIG_PREFIX=/home/claude/.local`
- [x] 1.4 `/etc/gitconfig` includes `/tmp/claude-docker-gitconfig`
- [x] 1.5 Drop the runtime-apt workaround; rewrite the "runs as root by design" and Chrome `--no-sandbox` rationale

## 2. entrypoint.sh

- [x] 2.1 Credential helpers written with `git config --file /tmp/claude-docker-gitconfig`
- [x] 2.2 `$HOME` instead of `/root`; fail with the migration pointer when a needed home dir is not writable

## 3. run.sh

- [x] 3.1 `--user 1000:1000`; remove `--cap-add DAC_OVERRIDE`/`FOWNER`
- [x] 3.2 Volumes and every bind target under `/home/claude`; tmpfs masks owned by 1000

## 4. Docs and examples

- [x] 4.1 README: box-user section and one-off migration; `/root` paths updated
- [x] 4.2 `examples/settings.docker.json` hook commands use `$HOME`

## 5. Verification (host: needs Docker)

- [x] 5.1 Image builds
- [x] 5.2 Migration commands run clean
- [x] 5.3 A box writes a file under `/mnt/c` that WSL shows as `aslojvari`
- [x] 5.4a tmpfs `uid=` option accepted (masks mount as uid 1000, mode 0700)
- [x] 5.4b Every `cd-*` launcher starts
- [x] 5.5 In a box: `flutter --version`, `git config --show-origin --get-all credential.https://github.com/.helper` under `--gh`, `/effort` persists

## 6. On archive

- [ ] 6.1 Replace `/root` with `/home/claude` in `specs/external-cli-tools`, `host-config-parity`, `persistent-session-storage`
