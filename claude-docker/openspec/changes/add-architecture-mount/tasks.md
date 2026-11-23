## 1. Launchers

- [x] 1.1 `cd-mep`: `cd_workspace "myEntryPoint"; mep=$ws`, then `cd_workspace "laslo/architecture"; arch=$ws`, as in `cd-tools`. `mep_test_db` uses `$mep`; `cd_test_db_run` passes `"$mep" "$arch" "$@"`. A comment line says why the model is mounted.
- [x] 1.2 `cd-brain`: the same with `brain=$ws`.
- [x] 1.3 `cd-board`: the same with `board=$ws`, in the `exec "$CD_RUN"` line.
- [x] 1.4 `bash -n` on the three launchers exits 0.

## 2. Docs

- [x] 2.1 launchers/README.md, the multi-workspace paragraph: name `cd-mep`, `cd-brain` and `cd-board` beside `cd-asr` and `cd-inat`, keep each path in a named variable, and add the shared-tree caveat (commit model edits by path).

## 3. Proof in the box

A scratch dev tree with copies of `_lib.sh`, `run.sh` and the three launchers, project and `laslo/architecture` dirs, and stub `docker`, `op` and `flock` on PATH. The stub `docker` logs its arguments and, for `run`, exits 0. `CLAUDE_DOCKER_BRAIN=0`, and a scratch `CLAUDE_DOCKER_ENV_FILE` (or equivalent) so no real env file is read.

- [x] 3.1 Each launcher with `-- --continue`, through the real `run.sh`: the logged `docker run` has `-w /workspaces/<project>`, `AGENT_BUS_SELF=<project key>`, the project's venv key, a read-write `/workspaces/architecture` mount, `--add-dir /workspaces/architecture`, and ends with `--continue`.
- [x] 3.2 `cd-mep` and `cd-brain`: the stub `docker compose` is called with the project's compose file.
- [x] 3.3 With `laslo/architecture` removed: each launcher exits 1 with `workspace not found: <dev>/laslo/architecture`. The `docker` and `op` stubs log nothing.
- [x] 3.4 `cd-board --ro`: both mounts end in `:ro`.

If the real `run.sh` can't be driven with stubs in the box, say which step blocks, fall back to a stub `run.sh` that prints its arguments for 3.1, and move the `-w` and env checks to 4.1.

## 4. Proof on the host (WSL, by the owner)

- [ ] 4.1 For each of `cd-mep`, `cd-brain`, `cd-board`, run inside the box: `pwd; echo $AGENT_BUS_SELF; ls /workspaces/architecture | head -3; touch /workspaces/architecture/.probe-$AGENT_BUS_SELF`. Expect the project's own directory and key.
- [ ] 4.2 On the host, `ls -a <dev>/laslo/architecture/.probe-*` lists the three probe files, then remove them.
- [ ] 4.3 In `cd-brain`: `git -C /workspaces/architecture remote -v` and `git -C /workspaces/architecture ls-remote origin HEAD`, so pushing the model from a box is known to work or not.
- [ ] 4.4 `cd-brain -- --continue` resumes the last brain conversation.

## 5. Validation and hand-off

- [x] 5.1 `openspec validate add-architecture-mount --strict` exits 0.
- [x] 5.2 Commit to `main` and push.
- [x] 5.3 With the owner's OK, reply on bus message `20261121T184852Z-492a25`: what changed, the host checks in 4, and the pointer line each project's `CLAUDE.md` needs (for cd-dev). The owner decides when to close it.
