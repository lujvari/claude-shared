## 0. Spikes (done 2026-11-16)
- [x] 0.1 Box-style container (`--cap-drop ALL`, default bridge or `--network host`) reaches a stack published on `127.0.0.1:<ephemeral>` via `host.docker.internal` / `127.0.0.1`: HTTP 200 both. WSL `docker` hits the same Docker Desktop engine (13 containers visible). Route stands.
- [x] 0.2 `.agent-bus` is the registry's parent; a box mounts only `<bus>/<key>` at `/bus` (`run.sh:513-535`), and a workspace that contains the bus gets it masked by tmpfs (`run.sh:482-485`). `<bus>/.stage/` is unreachable. Residual: two boxes with one key share a mailbox, so the per-key lock (2.1) is required.
- [x] 0.3 Compose v5.6.1: `container_name: !reset null` and `ports: !override [...]` merge as intended (`config` shows no container_name, port `127.0.0.1:0`); `up` mapped 32768, `down` clean.

## 1. Broker core (`tools/stage-broker/`)
- [x] 1.1-1.5 [R2,R3,R4,R6,R7] `tools/stage-broker/`: `lint.py`, `approval.py`, `stack.py`, `audit.py` (copy of slack-outbox's chain), `stage_broker.py` CLI (`approve|deny|pending|check|log|verify|register|unregister|watch|once`). Includes the R6 env test.

## 2. Transport
- [x] 2.1 [R1,R7] `service.py`: six verbs over `<bus>/<key>/.stage/req|res` (agent-bus mailbox, slack-outbox style queue dir); identity = mailbox dir, project = registry; refuses unknown verb, bad/unknown service, symlink, hardlink, oversize, bad JSON, bad/duplicate id, unregistered key, symlinked queue dirs; 10 requests per box per pass; every request audited.
- [x] 2.2 [R1,R4] `test_e2e.py`: two boxes post `up` through the queue, owner approves, both stacks run on distinct ports, `url`/`logs`/`down` work, box.b unaffected by box.a's `down`, compose edit after approval is refused. 72 tests green on Windows and WSL.

## 3. Launcher (`claude-docker`)
- [ ] 3.1 [R5] `--stage <project>` in `run.sh` + `launchers/_lib.sh`: refuse if a live box already has the key, `stage_broker.py register KEY PROJECT`, set `STAGE_QUEUE=/bus/.stage` in the box, `stage_broker.py teardown KEY` on exit. The ad-hoc test-postgres pre-start in `cd-mep` stays until pilot 4.3 passes.
- [ ] 3.2 [R5] Teardown on exit, crash cleanup, TTL reaper, caps (stacks/CPU/RAM). Tests: kill box -> stack gone; stack count over cap refused.

## 4. Pilot (myEntryPoint)
- [ ] 4.1 Host config for the file set: `docker-compose.yml` (+ `docker-compose.e2e.yml`), never `override.yml` (docker.sock, C:/dev mounts). Both lint clean with dummy env (checked). A `docker-compose.stage.yml` is only needed if the stage run needs something these lack. Stage env file must supply `OP_SERVICE_ACCOUNT_TOKEN` and `POSTGRES_PASSWORD` (compose requires both) as dummy values.
- [ ] 4.2 Skill in `laslo/kits`: up, E2E harness, report, down, and how to ask for approval on `held`.
- [ ] 4.3 Autonomous run on a small change. Pass = E2E green and the report matches a manual check by the owner.
