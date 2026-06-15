## Why

Developers using claude-docker against AWS accounts that hand them
static IAM-user access keys (not SSO) currently have two choices, both
unpleasant:

1. Write the keys to `~/.aws/credentials` on the host. The wrapper
   deliberately does not mount that file (`run.sh` excludes
   `~/.aws/credentials` and `~/.aws/cli/cache/` by design — long-lived
   secrets), so they are unreachable from inside the container.
2. Export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION`
   into the host shell before every `claude-docker --aws` invocation.
   The wrapper does forward those env vars, but the user is now
   responsible for getting them into the shell — either typing them on
   every session, or persisting them as User-scope environment
   variables on the host (where they live unprotected on disk and
   leak into every process).

Real failure mode observed (2026-06-15, Aegon AWS account): the user
was issued a console URL pointing at `eu-north-1.signin.aws.amazon.com`
(IAM-user sign-in, not Identity Center), with permission to create an
access-key pair. With no host-side AWS state and no clean place to put
the keys, the workflow stalled at "I have keys but no way to get them
into the container without exposing them to my whole user session."

The `--ado` and `--jira` flags already solved the equivalent shape for
single-secret tokens: when the host env var is unset and
`CLAUDE_DOCKER_<X>_OP_REF` is set, `run.sh` runs `op read` on the host
and forwards the resolved value. AWS access keys are the same problem
modulo cardinality: two required fields (access key ID + secret), one
common optional (session token), one nice-to-have non-secret (region).
1Password references support sub-field addressing
(`op://vault/item/field`), so a single `CLAUDE_DOCKER_AWS_OP_REF`
pointing at an item is enough — fields are resolved by canonical name.

This also restores symmetry with the SSO flow. SSO users can already
`aws sso login` on the host and the wrapper mounts `~/.aws/sso/cache`
read-only; their session credentials never have to round-trip through
host env vars. Static-key users had no analogous "credentials live in
managed storage, not host env" path. The 1P fallback fills that gap
without weakening the existing security invariants: `~/.aws/credentials`
remains unmounted, the host env-var forwarding path is unchanged, and
the new behaviour only fires when the user opts in by setting the env
var.

## What Changes

- **Add 1Password fallback for `--aws`** to `run.sh`: when `--aws` is
  set, `AWS_ACCESS_KEY_ID` is unset on the host, AND
  `CLAUDE_DOCKER_AWS_OP_REF` is set to an `op://` reference (e.g.
  `op://claude-docker/aegon-aws`), `run.sh` SHALL run `op read` on the
  host for each of the canonical sub-fields below and forward the
  resolved values as the matching `AWS_*` env vars:
    - `${ref}/access_key_id`     → `AWS_ACCESS_KEY_ID`     (required)
    - `${ref}/secret_access_key` → `AWS_SECRET_ACCESS_KEY` (required)
    - `${ref}/session_token`     → `AWS_SESSION_TOKEN`     (optional)
    - `${ref}/region`            → `AWS_REGION`            (optional)
  Required fields missing → silent no-op (matches `--ado` / `--jira`
  failure mode). Optional fields missing → just not forwarded. A
  trailing `/` on the ref is tolerated.
- **`AWS_REGION` precedence**: when `AWS_REGION` is already set on the
  host, the host value wins and the 1P region field is not read. The
  rationale matches `AWS_PROFILE` precedence: region is a session
  intent, not a secret tied to one specific item.
- **No change to the existing `--aws` mounts or env-var forwarding.**
  `~/.aws/config`, `~/.aws/sso/`, and the `AWS_*` env-var forwarding
  loop behave exactly as before. The new block sits alongside the
  existing `--ado` / `--jira` OP fallbacks and is gated on the same
  three-condition pattern they use.
- **Update README**: extend the `--aws` row in the Credential opt-in
  table and the Auth model table to mention the OP fallback. Add a
  small "Static keys via 1Password" subsection alongside the existing
  "AWS SSO flow" section to document the field-name convention.

Out of scope (deliberately):

- **Per-profile OP refs.** Users with multiple AWS accounts can switch
  by changing `CLAUDE_DOCKER_AWS_OP_REF` between invocations (the
  natural shape: one ref per account). A
  `CLAUDE_DOCKER_AWS_OP_REF_<PROFILE>` matrix would only matter when
  the in-container flow needs to swap profiles mid-session, which is
  uncommon for static-key accounts; SSO already handles that case
  via `aws --profile X`.
- **SSO via 1Password.** SSO sessions live in `~/.aws/sso/cache` as a
  set of bearer tokens with non-trivial refresh logic; replicating
  that out of 1P would require mirroring the AWS CLI's cache-file
  format. The existing host-mount path covers SSO; the OP fallback is
  for static keys only.
- **Field-name override.** The canonical sub-fields are hard-coded
  (`access_key_id`, `secret_access_key`, `session_token`, `region`)
  to keep the contract simple. Users with existing 1P items under
  different field names create a new item / add the canonical fields
  — one-time setup cost, then no env-var matrix to manage. If a real
  need for override emerges (multi-org with externally-managed 1P
  schemas), it can be added back as a follow-up.
- **Reading AWS keys from a credential file `op` writes to.** A
  pattern some users adopt is `op inject` to materialise a credentials
  file at session start. That works today without any wrapper change
  by writing to `~/.aws/credentials`-style file in a tmpfs and
  pointing `AWS_SHARED_CREDENTIALS_FILE` at it via `--aws` env
  forwarding — but it's user-side composition, not a wrapper feature.

## Capabilities

### New Capabilities

None. This change extends an existing capability.

### Modified Capabilities

- `external-cli-tools`: extends the `--aws` opt-in flag with an `op
  read` fallback for static-key credentials. The "credentials opt-in"
  invariant is preserved — the new behaviour only fires when both the
  flag is set and `CLAUDE_DOCKER_AWS_OP_REF` is explicitly exported, so
  no AWS credentials reach the container without two acts of opt-in
  (the flag + the env-var reference).

## Impact

- **Code**: `claude-docker/run.sh` (one new gated block beside the
  existing `--ado` / `--jira` OP fallbacks; one help-text addition;
  one comment update on the existing `--aws` mount block).
- **Docs**: `claude-docker/README.md` (extended `--aws` rows in two
  tables; new "Static keys via 1Password (`--aws`)" subsection
  alongside the SSO flow section).
- **Specs**: delta to `external-cli-tools`.
- **No breaking changes.** Existing `--aws` behaviour is unchanged;
  the fallback is purely additive and gated on a new env var.
- **Dependencies**: no new binaries. The image does not need `op`
  inside — resolution happens on the host (same as `--ado` / `--jira`).
