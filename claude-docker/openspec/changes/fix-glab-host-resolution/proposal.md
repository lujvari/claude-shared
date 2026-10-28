## Why

Reported by the `sbp.ai.inat` box on 2026-10-28. There are two faults, and both
come from the host's glab config leaking into how a box picks its GitLab hosts:

- **glab in the box has no host.** `run.sh` always tmpfs-masks
  `~/.config/glab-cli`, so glab inside the box knows no hosts and falls back to
  gitlab.com. `glab mr create` in an sbp.gitlab repo then fails on host
  resolution.
- **The SBP token is offered to gitlab.com.** `_extract_glab_hosts` copies
  every host in the WSL `~/.config/glab-cli/config.yml` into
  `CLAUDE_DOCKER_GITLAB_HOSTS`. That list included gitlab.com, so the entrypoint
  installed a credential helper that offers the sbp.gitlab token to gitlab.com,
  which answers 401.

## What Changes

- **No glab-config parsing.** Delete `_extract_glab_hosts`. Under `--glab` the
  host list is `CLAUDE_DOCKER_GITLAB_HOSTS` when set, and otherwise the
  entrypoint's existing `gitlab.com` default. The host glab config plays no
  part in a launch.
- **Forward `GITLAB_HOST`.** With `--glab`, `run.sh` forwards `GITLAB_HOST`
  when it is set on the host, the same way it forwards `GITLAB_TOKEN`. glab
  uses it as its default host.
- **Explicit SBP launchers.** `cd-cis`, `cd-inat`, `cd-asr` and `cd-ta` each
  export `GITLAB_HOST=sbp.gitlab.schubergphilis.com` and
  `CLAUDE_DOCKER_GITLAB_HOSTS=sbp.gitlab.schubergphilis.com` before `exec`.
  `run.sh` derives neither value.
- **Docs.** Update the `--glab` help text in `run.sh`, the README `--glab` row
  and `specs/external-cli-tools` to match. The spec's `--glab` text still
  describes the old read-only config mount. This change replaces that text
  rather than layering another "superseded" note on top.

## Unchanged

Token handling. `GITLAB_TOKEN` still comes only from the host env var or the
`CLAUDE_DOCKER_GITLAB_OP_REF` op-ref. The fail-closed gate, the always-on
glab-cli tmpfs mask, and the `--gh` host enumeration (`_extract_gh_hosts`) stay
as they are.

## Acceptance

In a `cd-inat` box after the change:

1. `glab mr list` in the inat repo works with no extra environment setup.
2. `git config --show-origin --get-regexp '^credential\..*helper'` lists a
   helper for `https://sbp.gitlab.schubergphilis.com` only. There is no
   gitlab.com entry and no `insteadOf` rewrite.
3. A draft MR opened from a scratch branch in sbp-ai/kits succeeds. It is then
   closed and the branch deleted. If GitLab refuses for lack of scope, the run
   stops and the owner widens the token. The box never touches the token.

Also: `run.sh --glab` with neither variable set forwards no
`CLAUDE_DOCKER_GITLAB_HOSTS`, and the entrypoint falls back to gitlab.com.

## Out of scope

- Migrating to a glab config written inside the box.
- Changing the gitlab.com default for non-SBP `--glab` use.
- Token scope or rotation.

## Impact

- Files: `run.sh`, `launchers/cd-{cis,inat,asr,ta}`, `README.md`,
  `openspec/specs/external-cli-tools/spec.md` (on archive).
- Anyone who used `--glab` without a launcher and relied on the glab-config
  host list now gets gitlab.com unless they set `CLAUDE_DOCKER_GITLAB_HOSTS`.
  Today that applies only to the four launchers above, which set it
  explicitly.
