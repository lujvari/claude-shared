## Why

Brain's in-box test suite flakes: about half of full runs stall 11-60 s on one
TCP connect to `host.docker.internal:47401`, and at 60 s asyncpg raises
`TimeoutError`. Measured from the brain box (2026-11-25): not DNS, not Postgres
auth; the Docker Desktop port forward (box -> host 127.0.0.1:47401 ->
`brain-test-postgres`) drops connects under the suite's load. A box that sits
on the database's own compose network talks to it container-to-container and
never touches the forward.

## What Changes

- **`--braindb` joins the box to `brain-test-postgres`'s network.** `run.sh`
  reads the network from the running container (`docker inspect`) rather than
  hardcoding the compose project name, and passes it as `docker run --network`.
- **`BRAIN_TEST_DSN` is rewritten** in the box to `brain-test-postgres:5432`.
  Only the URL's host and port change; credentials, database and query string
  are kept. The host-side value (env or 1Password) is untouched, so host-side
  tests keep using `127.0.0.1:47401`.
- **Fail loudly, no fallback**: the container not running, a network count
  other than one, a DSN that is not a `scheme://` URL, or `--braindb` combined
  with `--host-net` / `CLAUDE_DOCKER_NETWORK` each abort the launch before
  `docker run`.
- **README** and **`cd-brain`'s header comment** describe the network path
  instead of `host.docker.internal:47401`.

Out of scope: `--mepdb` (same forward, no reported flake); `compose.test.yml`
in laslo/brain (needs no change); joining two networks at once.

## Capabilities

### Modified Capabilities

- `external-cli-tools`: the Brain test-database opt-in reaches the database
  over its compose network.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: `claude-docker/README.md`, `claude-docker/launchers/cd-brain` (comment).
- **Behaviour change**: `--braindb` now needs `brain-test-postgres` running at
  launch. `cd-brain` already brings it up first; a bare `claude-docker
  --braindb` without it now aborts instead of launching a box that can't
  reach its database.
