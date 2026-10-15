> Retroactive record: implemented in eed753a on 2026-07-14, written 2026-10-15 to close spec drift.

## Why

On a corporate VPN the host uplink MTU drops below Docker's bridge MTU
(1500). Docker Desktop's bridge/NAT egress ignores the container and bridge
MTU and silently drops oversized TLS handshake packets. Inside the container
this surfaces as a bogus certificate/connection error
(`UNKNOWN_CERTIFICATE_VERIFICATION_ERROR`) even though the Claude login is
valid, and lowering the bridge MTU does not help. Running on the host network
namespace uses the host uplink, with the correct MTU, directly.

## What Changes

- **Add `--host-net`**: runs the container with `docker run --network host`
  instead of the default bridge.
- **Add `CLAUDE_DOCKER_NETWORK`**: names any docker network to pass as
  `--network`; `--host-net` sets it to `host`. Unset or empty means no
  `--network` argument (Docker's default bridge).
- **Statusline**: a set network adds `net:<network>` to `CLAUDE_DOCKER_FLAGS`.
- **Off by default.** Help states the trade-off: the container loses network
  isolation and can reach host localhost/LAN services (with WSL2 mirrored
  networking, the Windows localhost). The filesystem sandbox, dropped
  capabilities and `no-new-privileges` are unchanged.

Out of scope (deliberately):

- Fixing the MTU problem on the bridge itself.
- README documentation (eed753a touched only `run.sh`).

## Capabilities

### New Capabilities

- `container-network`: how the launcher chooses the container's network.

### Modified Capabilities

None.

## Impact

- **Code**: `claude-docker/run.sh`.
- **Docs**: help text only; no README row.
- **Specs**: new capability `container-network`.
- **Security**: with the flag, the container shares the host network
  namespace. Without it, nothing changes.
