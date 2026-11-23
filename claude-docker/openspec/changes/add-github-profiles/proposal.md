<!-- Rewrite, not patch: v1 (add-inat-github) let the launcher pick the token by
     exporting the op-ref and unsetting GH_TOKEN. Gate 5 showed the env file
     re-exports a GH_TOKEN line after the launcher's unset, and --gh exposes the
     shared gh login. The choice has to be enforced in run.sh, as ADO profiles are. -->
## Why

inat is moving to GitHub (`schubergphilis/inat`, inat spec 0027). The cd-inat
box needs to push there, open PRs and read CI logs. Plain `--gh` would hand it
the owner's personal token: the env file's `CLAUDE_DOCKER_GITHUB_OP_REF`
(`github-pat`), any `GH_TOKEN`/`GITHUB_TOKEN` in the shell or the env file,
or the `gh` login persisted on the shared `claude-code-root` volume. A
launcher can't rule these out by itself: `run.sh` loads the env file after the
launcher has run, and only skips keys that are already non-empty
(`run.sh:633`).

`--ado` had the same problem for a customer org and solved it with named
profiles (`lib/ado-profile.sh`, add-ado-profiles). GitHub gets the same shape.

## What Changes

- **Named GitHub profiles** (`lib/gh-profile.sh`, sourced by `run.sh` right
  after the ADO profile, before the env forwarding list is built). With
  `CLAUDE_DOCKER_GITHUB_PROFILE=<name>` and `--gh`:
  - the token comes only from `CLAUDE_DOCKER_GITHUB_<NAME>_OP_REF`. A host
    `GH_TOKEN`/`GITHUB_TOKEN`, whether from the shell or the env file, is
    dropped with a note, and `CLAUDE_DOCKER_GITHUB_OP_REF` is replaced by the
    profile ref, so the existing preflight and `op read` paths read the
    profile's item and the `gh auth token` CLI fallback stays off;
  - `CLAUDE_DOCKER_GITHUB_HOSTS` is pinned to `github.com`, so the
    entrypoint's git helper is never set up for a GitHub Enterprise host
    from the host's gh config;
  - the persisted `~/.config/gh` login is masked with a tmpfs, as without
    `--gh`;
  - a profile with no token aborts the launch, and `CLAUDE_DOCKER_OP_OPTIONAL`
    does not apply.
  - `CLAUDE_DOCKER_GITHUB_PROFILE` is read from the launching env only; the
    env-file loader skips it, like `CLAUDE_DOCKER_ADO_PROFILE`.
- **`cd-inat`** sets profile `inat` with
  `CLAUDE_DOCKER_GITHUB_INAT_OP_REF` defaulting to
  `op://claude-docker/inat-github-ro/credential` (overridable like `cd-apg`'s
  profile ref), and adds `--gh`. Its GitLab exports are unchanged.
- **Docs**: README "Named GitHub profiles" next to "Named ADO profiles";
  `run.sh --help` for `--gh` and the new variable; launchers README notes that
  `cd-apg` and `cd-inat` pick their credential through a profile.

Out of scope:

- The token itself and its org-owner approval. Until approval lands, the repo
  answers 403/404 even with everything right.
- Renaming the `inat-github-ro` item (it holds a read-write token): the
  owner's call; the env file can override the ref meanwhile.
- Profile hosts other than `github.com`, and a statusline tag for GitHub
  profiles. Add them when a profile needs one.
- The shared `~/.gitconfig` `gh auth git-credential` helper on the volume.
  With the gh login masked and `GH_TOKEN` guaranteed, it can only hand out the
  profile token.
- The token being visible to every process in the box: true of every `--gh`
  token (README "One flag = one credential").

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `external-cli-tools`: `--gh` takes a named profile.
- `launchers`: cd-inat forwards GitHub through profile `inat`.

## Impact

- **Code**: `claude-docker/lib/gh-profile.sh` (new, precedent
  `lib/ado-profile.sh`), `lib/test_gh_profile.py` (new, precedent
  `lib/test_ado_profile.py`), `run.sh`, `launchers/cd-inat`.
- **Docs**: `README.md`, `launchers/README.md`, `run.sh --help`.
- Boxes without `CLAUDE_DOCKER_GITHUB_PROFILE` behave exactly as before.
- Launchers and `run.sh` are symlinked from this checkout: live on the next
  `cd-inat` launch, nothing to install.
