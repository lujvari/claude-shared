## MODIFIED Requirements

### Requirement: Credentials opt-in

The `--glab` bullet is replaced with:

- `--glab`: mount no glab config. `/home/claude/.config/glab-cli` is always tmpfs-masked. Forward `GITLAB_TOKEN`, taken from the host env var or `op read "$CLAUDE_DOCKER_GITLAB_OP_REF"`. Forward `GITLAB_HOST` when it is set on the host. Forward `CLAUDE_DOCKER_GITLAB_HOSTS` when it is set on the host. `run.sh` SHALL NOT derive any GitLab host from the host glab config. When `CLAUDE_DOCKER_GITLAB_HOSTS` is unset, the entrypoint installs the GitLab credential helper for `gitlab.com` only.

The scenario "--glab grants read-only token access" is replaced with:

#### Scenario: --glab host list comes only from the environment

- **GIVEN** the host `~/.config/glab-cli/config.yml` lists `gitlab.com` and `sbp.gitlab.schubergphilis.com`
- **AND** `CLAUDE_DOCKER_GITLAB_HOSTS=sbp.gitlab.schubergphilis.com` is exported
- **WHEN** the user runs `claude-docker --glab ~/repo`
- **THEN** the container's git credential helpers cover `https://sbp.gitlab.schubergphilis.com` only

#### Scenario: --glab forwards GITLAB_HOST

- **GIVEN** `GITLAB_HOST=sbp.gitlab.schubergphilis.com` is exported on the host
- **WHEN** the user runs `claude-docker --glab ~/repo`
- **THEN** `echo $GITLAB_HOST` inside the container prints `sbp.gitlab.schubergphilis.com`
- **AND** `glab mr list` in an sbp.gitlab repo resolves that host without further setup

#### Scenario: SBP launchers pin the GitLab host

- **WHEN** `cd-cis`, `cd-inat`, `cd-asr` or `cd-ta` starts a box
- **THEN** the launcher has exported `GITLAB_HOST` and `CLAUDE_DOCKER_GITLAB_HOSTS`, both set to `sbp.gitlab.schubergphilis.com`, before `exec`ing `run.sh`
