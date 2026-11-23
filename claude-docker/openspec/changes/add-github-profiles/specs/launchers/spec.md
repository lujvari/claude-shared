## ADDED Requirements

### Requirement: cd-inat uses GitHub profile inat

The `cd-inat` launcher SHALL launch with `--gh` and `--glab`, with `CLAUDE_DOCKER_GITHUB_PROFILE=inat` and `CLAUDE_DOCKER_GITHUB_INAT_OP_REF` defaulting to `op://claude-docker/inat-github-ro/credential`. Its GitLab settings SHALL stay unchanged.

#### Scenario: cd-inat gets the inat token and keeps GitLab

- **WHEN** the owner runs `cd-inat`
- **THEN** 1Password is asked for `op://claude-docker/inat-github-ro/credential` and never for the default GitHub ref
- **AND** the box still gets `GITLAB_HOST` and `CLAUDE_DOCKER_GITLAB_HOSTS` set to `sbp.gitlab.schubergphilis.com`
