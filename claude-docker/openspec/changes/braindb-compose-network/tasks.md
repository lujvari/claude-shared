## 1. run.sh

- [x] 1.1 After the `--host-net` block: under `--braindb`, refuse a preset `NETWORK`; `docker inspect brain-test-postgres` must be running with exactly one network; append `--network <it>` to `MOUNT_ARGS`
- [x] 1.2 Same block: when `BRAIN_TEST_DSN` is set, rewrite its URL authority to `brain-test-postgres:5432` (keep userinfo, path, query); abort on a non-URL value without echoing it
- [x] 1.3 `--help` entry for `--braindb` says it joins the network and rewrites the DSN

Proof: `bash -n run.sh`; the rewrite function exercised on sample DSNs (with and without userinfo, query string, `@` in the password); the inspect/abort paths run against a stub `docker` on `PATH`.

## 2. Documentation

- [x] 2.1 README: `--braindb` table rows and the Brain paragraph describe the network path and the new launch requirement
- [x] 2.2 `cd-brain` header comment: boxes reach the database on its compose network, not `host.docker.internal:47401`

## 3. Live (host, owner)

- [ ] 3.1 Relaunch `cd-brain`; in the box `psql "$BRAIN_TEST_DSN" -c 'select 1'` succeeds and `getent hosts brain-test-postgres` resolves
- [ ] 3.2 Brain box reruns its full suite several times with no connect stall
