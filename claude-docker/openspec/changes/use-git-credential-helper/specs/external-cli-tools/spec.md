## MODIFIED Requirements

### Requirement: --gh and --glab inject git insteadOf rewrites

When `--gh` is set and a GitHub token reaches the container (via host env var `GH_TOKEN` / `GITHUB_TOKEN`, or the existing `gh auth token` fallback in `run.sh`), the container's startup SHALL configure in-container `git` to authenticate against each opted-in GitHub host by writing a **system-level git credential helper**, NOT a `url.<host>.insteadOf` URL rewrite. For each host the entrypoint SHALL write `git config --system credential.https://<host>.username oauth2` and `git config --system credential.https://<host>.helper <helper>`, where `<helper>` is an inline POSIX-sh function that, on the `get` operation, prints `password=<token>` by reading the token from the forwarded environment variable **at auth time** (e.g. `$GITLAB_TOKEN`). The stored helper SHALL contain only a reference to the env var, never the token value, so the secret MUST NOT be written to `/etc/gitconfig`. The host list SHALL come from `CLAUDE_DOCKER_GITHUB_HOSTS` (a comma-separated env var populated by `run.sh`); when empty or unset and a token is present, the entrypoint SHALL default to `github.com`. The same SHALL apply to `--glab` / `GITLAB_TOKEN` / `CLAUDE_DOCKER_GITLAB_HOSTS` (default `gitlab.com`) and to `--ado` / `AZURE_DEVOPS_EXT_PAT` / `CLAUDE_DOCKER_ADO_HOSTS` (default `dev.azure.com`). The injected token SHALL NOT appear in the output of any git command that prints a URL (`git remote -v`, `git fetch -v`, `git ls-remote`, `git remote prune`, clone/push progress) — because no URL rewrite is configured, those commands SHALL show bare `https://<host>/…` URLs. The config SHALL be written via `git config --system` (to `/etc/gitconfig`), which lives in the container's writable layer and is discarded on `docker run --rm` exit — so nothing persists across container exits via the `claude-code-root` named volume. The injection SHALL NOT override a user's own `git config --global` (`/root/.gitconfig`) credential or insteadOf entry (precedence `--local > --global > --system`).

#### Scenario: --glab configures a credential helper, not a URL rewrite

- **GIVEN** the host exports `GITLAB_TOKEN=glpat_x`
- **WHEN** user runs `claude-docker --glab ~/repo`
- **THEN** inside the container, `git config --system --get
  credential.https://gitlab.com.username` prints `oauth2`
- **AND** `git config --system --get credential.https://gitlab.com.helper`
  prints a helper string containing the literal text `$GITLAB_TOKEN` and
  NOT the value `glpat_x`
- **AND** `git config --system --get-all url.https://gitlab.com.insteadOf`
  prints nothing (no URL rewrite is configured)

#### Scenario: token is supplied to git auth without appearing in the URL

- **GIVEN** a `--glab` session with a valid `GITLAB_TOKEN` for
  `sbp.gitlab.schubergphilis.com`
- **WHEN** `git ls-remote https://sbp.gitlab.schubergphilis.com/<priv>/<repo>`
  runs inside the container
- **THEN** the command authenticates and succeeds (exit 0) without
  prompting for credentials
- **AND** `git ls-remote --get-url <that bare URL>` prints the bare URL
  with no `oauth2:<token>@` prefix

#### Scenario: token does not leak into git URL-printing commands

- **GIVEN** a `--glab` session whose repo has a bare `origin`
  (`git config --get remote.origin.url` shows no credentials)
- **WHEN** the user runs `git remote -v`, `git fetch -v`, or
  `git remote prune origin`
- **THEN** the printed `URL:` / `From` lines show the bare
  `https://<host>/…` URL
- **AND** no `oauth2:<token>@<host>` form appears in any of that output

#### Scenario: token value is never written to /etc/gitconfig

- **GIVEN** a `--gh` session with a real `GH_TOKEN`
- **WHEN** `git config --system --list` runs inside the container
- **THEN** the output includes the `credential.https://github.com.helper`
  entry referencing `${GH_TOKEN:-$GITHUB_TOKEN}`
- **AND** the literal token value does not appear anywhere in the output

#### Scenario: GitHub helper honours GH_TOKEN over GITHUB_TOKEN

- **GIVEN** both `GH_TOKEN` and `GITHUB_TOKEN` are exported with different
  values
- **WHEN** git authenticates against `github.com`
- **THEN** the helper supplies the `GH_TOKEN` value (the `${GH_TOKEN:-$GITHUB_TOKEN}`
  precedence)
- **AND** when only `GITHUB_TOKEN` is set, the helper supplies that value

#### Scenario: token does not leak across container exits

- **GIVEN** a prior container run completed with `--gh` and a real `GH_TOKEN`
- **WHEN** a subsequent `claude-docker ~/repo` runs without `--gh`
- **THEN** `git config --system --list` inside the second container shows
  no `credential.*` helper entries
- **AND** no token from the prior session is readable inside the container

#### Scenario: user global config wins over system injection

- **GIVEN** a user has a `git config --global credential.https://github.com.helper`
  persisted to `/root/.gitconfig` via `claude-code-root`
- **WHEN** the user runs `claude-docker --gh ~/repo`
- **THEN** git's precedence (`--global > --system`) uses the user's helper
- **AND** the `--system` helper remains configured but deferred

#### Scenario: malformed token with embedded newlines is rejected with a clear warning

- **GIVEN** the host exports `GITLAB_TOKEN` to a multi-line value (e.g. a
  broken `export GITLAB_TOKEN="$(glab auth token 2>/dev/null)"` capturing
  help text)
- **WHEN** user runs `claude-docker --glab ~/repo`
- **THEN** the entrypoint detects control characters in the token, prints a
  single-line warning to stderr identifying the affected host group, and
  skips the credential injection for that group
- **AND** the container starts normally; any other valid token group is
  unaffected

#### Scenario: no opt-in flag means no credential injection

- **GIVEN** no host token is exported and no opt-in flag is passed
- **WHEN** user runs `claude-docker ~/repo`
- **THEN** the entrypoint runs but injects no credential helpers
- **AND** `git config --system --list` inside the container shows no
  `credential.*` entries
