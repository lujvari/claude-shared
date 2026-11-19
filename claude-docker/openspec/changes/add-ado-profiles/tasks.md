Plan v2. v1 assumed a box sees only the credentials `run.sh` forwards. That is
false: every box shares the `claude-code-root` home volume, and an SBP
`az devops login` PAT was sitting in it, readable from every box. It was
deleted on 2026-11-19. v2 adds masking for that state.

v2 also drops the entrypoint change. Under a profile, `run.sh` sets
`CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com/<org>,…`. The existing `inject_credential`
writes `credential.https://<host>.*` keys, and those match on path as they
are. This was verified on git 2.53 without `useHttpPath`: the `aamnld` URL
and the `aamnld@` URL match; `sbp-controltower` and `aamnldx` do not. So images
from 028bbf6 (2026-06-25, the move from insteadOf to the helper) onward behave
the same. The only image change is pre-creating the three mask mountpoints
(task 2.10), so a fresh volume doesn't end up with a root-owned `~/.azure`. On
the existing volume those directories already exist, owned by the box user.

Profile resolution lives in a sourced `lib/ado-profile.sh` so it can be
unit-tested in the box. `run.sh` has no test harness and no dry run.

The `apg` op-ref sits in `cd-apg` next to the profile and org, so the box is
self-contained and the owner only creates the 1Password item. An op-ref is a
pointer, not a secret.

## Blast radius and REQ → proof

`CLAUDE_DOCKER_ADO_ORG` becomes a comma list. Its call sites, from a grep:
- `run.sh:315` (help text)
- `lib/token-probe.sh:84-85` (task 3)
- `launchers/cd-ct:23` and `launchers/cd-ws13:10` (single value, still valid)
- `lib/test_token_probe.py:103,147` (single value, still valid)

`CLAUDE_DOCKER_ADO_HOSTS` consumers:
- `run.sh:1489-1491` (task 2.4)
- `entrypoint.sh:156` (unchanged; reads what `run.sh` forwards)
- `README.md:40,503` (task 5)

| Spec scenario | Proof |
|---|---|
| Profile PAT reaches the box (+ `ado:apg` tag) | 1.2 ok case; 6.3 statusline + `ls-remote` |
| Host PAT does not leak | 1.2 host PAT dropped; 2.8 order check; 6.3 with a dummy host PAT exported |
| Env file cannot select a profile | 2.8 loader check; 6.5 |
| Missing or unreadable op-ref aborts | 1.2 missing ref; 6.4 bogus ref with `OP_OPTIONAL=1` |
| Empty or invalid org list aborts | 1.2 |
| Invalid profile name aborts | 1.2 |
| Admin refused under a profile | 1.2 (both flag combos) |
| Profile without an ADO flag is inert | 1.2 (resolver not entered); 2.8 |
| git offers the PAT to profile orgs only | 2.9 in the box, with no entrypoint change; 6.3 on the host |
| Probe covers every profile org | 3.2 |
| No profile keeps today's behaviour | 1.2 pass-through; existing probe tests; 6.5 |
| Client box cannot read SBP az devops state | 6.3 (`ls -A` empty in cd-apg) |
| Default ADO box keeps its defaults | 6.5 |
| Profile box writes do not persist | 6.4b |

## 1. lib/ado-profile.sh (new; precedent: lib/token-probe.sh, sourced by run.sh)

- [x] 1.1 `ado_profile_resolve` is safe under bash 3.2 (as `run.sh` is: no `${x^^}`, no `mapfile`; upper-case with `tr`; never expand the org array before its non-empty check) and under `set -euo pipefail`, and every failure path does an explicit `echo … >&2; return 1`, because `|| exit 1` turns `set -e` off inside the function.
  - **Inputs:** `WITH_ADO`, `WITH_ADO_ADMIN`, `CLAUDE_DOCKER_ADO_PROFILE` and the derived variables.
  - **Outputs:** `ADO_PROFILE`, `ADO_OP_REF_VAR` (the profile's op-ref variable name, for error messages) and `ADO_OP_REF`, all set on every path, empty by default. The orgs leave only through the exported `CLAUDE_DOCKER_ADO_ORG` and `CLAUDE_DOCKER_ADO_HOSTS`.
  - **No profile:** `ADO_OP_REF=${CLAUDE_DOCKER_ADO_OP_REF:-}`; nothing else is touched.
  - **Profile:**
    - validate the name;
    - refuse when `WITH_ADO_ADMIN=1`;
    - if `WITH_ADO` is not 1, return 0 (inert);
    - the op-ref comes from `CLAUDE_DOCKER_ADO_<NAME>_OP_REF` through `${!v:-}`, and must be non-empty;
    - the orgs: non-empty, comma-split, no empty items, each `^[A-Za-z0-9-]+$`.
  - **Profile, on success:**
    - `unset AZURE_DEVOPS_EXT_PAT`, printing one note when it was set, so a deliberate host PAT doesn't vanish silently;
    - `export CLAUDE_DOCKER_ADO_ORG=$ADO_ORGS` (for the probe);
    - `export CLAUDE_DOCKER_ADO_HOSTS=dev.azure.com/<org>,…`.
- [x] 1.2 `lib/test_ado_profile.py`, in the style of `test_token_probe.py`. Each case runs `bash -c 'set -euo pipefail; . lib/ado-profile.sh; ado_profile_resolve || exit 1; declare -p …'` with a clean env. This is the exact call form `run.sh` uses, so errexit is off inside the function just as it is in production.
  - Cases:
    - no profile passes through;
    - profile ok (checks `CLAUDE_DOCKER_ADO_ORG` and `CLAUDE_DOCKER_ADO_HOSTS`);
    - host PAT dropped, with a note;
    - missing op-ref;
    - empty orgs, `a/b`, `a,,b`;
    - names `apg;x` and `APG`;
    - admin refused with `WITH_ADO=1` and with `WITH_ADO=0`;
    - `WITH_ADO=0` with a profile is inert (no unset, no exports).
  - **Proof:** `python3 -m unittest lib/test_ado_profile.py` passes in the box.

## 2. run.sh

- [x] 2.1 In the env-file loader (~run.sh:612), skip the key `CLAUDE_DOCKER_ADO_PROFILE`, with a one-line comment saying why.
- [x] 2.2 After the loader (~run.sh:626): source the lib and set `ADO_PROFILE= ADO_OP_REF_VAR= ADO_OP_REF=`. Then, if `WITH_ADO=1` or `WITH_ADO_ADMIN=1`, call `ado_profile_resolve || exit 1`. When no profile is set, `ADO_OP_REF` falls back to `CLAUDE_DOCKER_ADO_OP_REF`. This runs before `ENV_VARS` (~run.sh:627) and before any `op` call.
- [x] 2.3 Use `$ADO_OP_REF` in place of `CLAUDE_DOCKER_ADO_OP_REF` in the preflight (~run.sh:942) and the fallback block (~run.sh:1153).
- [x] 2.4 Hosts forward (~run.sh:1490) is unchanged. It already forwards `CLAUDE_DOCKER_ADO_HOSTS`, which the resolver has set to the org paths under a profile.
- [x] 2.5 Statusline (~run.sh:1521): `ado:$ADO_PROFILE` when a profile is set, otherwise `ado`.
- [x] 2.6 Right after the `cred_require` lines (~run.sh:1763), before `launch_blocked`: if `ADO_PROFILE` is set and `${AZURE_DEVOPS_EXT_PAT:-}` is empty, print an error naming `$ADO_OP_REF_VAR`, say that `CLAUDE_DOCKER_OP_OPTIONAL` does not apply to ADO profiles, and `exit 1`.
- [x] 2.7 Mask (~run.sh:1691, inside `EPHEMERAL=0`): unless `WITH_ADO=1` and no profile is set, add `--tmpfs` for `/home/claude/.azure/azuredevops` and `/home/claude/.azure-devops` with `$TMPFS_USER_OPTS`. The comment cites the 2026-11-19 finding. Precedent: the gh and glab-cli masks next to it.
- [x] 2.8 Help text:
  - add the profile to `--ado` (~run.sh:116);
  - add the env-var section entries (~run.sh:315) for `CLAUDE_DOCKER_ADO_PROFILE` (launching env only), `_<NAME>_OP_REF` and `_<NAME>_ORGS`;
  - mark `CLAUDE_DOCKER_ADO_ORG` as a comma list.
- [x] 2.9 Proof in the box:
  - `bash -n run.sh lib/ado-profile.sh` passes.
  - `grep -n` shows, in order, the resolver call, then `ENV_VARS+=(AZURE_DEVOPS_EXT_PAT)`, then the forwarding loop. This checks that the leak can't come back through ordering.
  - Copy `entrypoint.sh`'s unchanged `inject_credential` function into a scratch script, with `GIT_RUNTIME_CONFIG` set to an absolute scratch path, never `/tmp/claude-docker-gitconfig`. Feed it the hosts string the resolver produced in 1.2. Then run `git credential fill` for the four spec URLs under `AZURE_DEVOPS_EXT_PAT=dummy GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=<scratch> GIT_TERMINAL_PROMPT=0`, so neither this box's own helpers nor the shared `~/.gitconfig` can answer, and a real PAT can never print. Print only whether a `password=` line came back: yes, yes, no, no.
- [x] 2.10 Dockerfile (~:579): add `/home/claude/.azure`, `/home/claude/.azure/azuredevops` and `/home/claude/.azure-devops` to the `install -d -o 1000` list. Precedent: the gh, glab-cli and terraform.d mask mountpoints in the same list. Proof: `grep -c azure Dockerfile` goes up by 3; the build itself happens in 6.2.

## 3. lib/token-probe.sh

- [x] 3.1 Split `CLAUDE_DOCKER_ADO_ORG` on commas and probe each org, for both the ext PAT and the admin PAT.
  - With one org, the probe name and warning stay `ado` / `--ado`, so existing tests are unchanged.
  - With several orgs, each warns as `--ado@<org>`, and `TOKEN_PROBE_REJECTED` gets `ado@<org>`.
  - Whether ADO answers 401 or 203/403 for a PAT used against another org is unverified. If it doesn't answer 401, the probe stays quiet (fail-quiet, as today).
- [x] 3.2 Tests, using orgs `orga` and `orgb`. Neither is a substring of the other, because the stub matches by substring.
  - two orgs, `orgb` 401: one warning, `--ado@orgb`;
  - two orgs, both 200: quiet, two calls.
  
  **Proof:** `python3 -m unittest lib/test_token_probe.py` passes.

## 4. launchers/cd-apg

- [x] 4.1 Exports:
  - `CLAUDE_DOCKER_ADO_PROFILE=apg`
  - `CLAUDE_DOCKER_ADO_APG_OP_REF="${CLAUDE_DOCKER_ADO_APG_OP_REF:-op://claude-docker/AzureDevOps PAT APG/credential}"`
  - `CLAUDE_DOCKER_ADO_APG_ORGS=aamnld`
  
  Add `--ado` to `exec`. Add a comment: customer org, own PAT, never the SBP one.
- [x] 4.2 **Proof:** `bash -n launchers/cd-apg`.

## 5. README

- [x] 5.1 Update:
  - `--ado` row (README:40) and auth-model row: `ado:<name>`, org-scoped.
  - New "Named ADO profiles" subsection in the 1Password section (~README:359):
    - the variables;
    - the no-fallback and env-file rules;
    - the masking;
    - the hand-over for placing a profile PAT.
  - Git helper scope (~README:503): profiles scope by org.
- [x] 5.2 **Proof:** `grep -n 'ADO_PROFILE' README.md` hits the subsection.

## 6. Host steps (owner, WSL)

Rebuild the image for 2.10. Only a fresh volume depends on it.

- [x] 6.1 Create the PAT in `dev.azure.com/aamnld`:
  - Organization: `aamnld` only;
  - Scopes: Code → Read.
  
  Store it in 1Password vault `claude-docker`, item `AzureDevOps PAT APG`, field `credential`. Copy a clone URL from the ADO web UI and check the org's spelling and case against `CLAUDE_DOCKER_ADO_APG_ORGS`. **Proof:** `op read "op://claude-docker/AzureDevOps PAT APG/credential" | wc -c` prints a non-zero count.
- [ ] 6.2 No install step is needed: `~/bin/cd-*` are symlinks into the checkout. Rebuild the image (the `docker build` line in README "one-off migration") so the Dockerfile mountpoints are in place before a volume is ever recreated.
- [x] 6.3 Run `AZURE_DEVOPS_EXT_PAT=dummy cd-apg`. Check:
  - one note that the host PAT was dropped;
  - tag `ado:apg`;
  - no rejected-token warning.
  
  In the box:
  - `echo len=${#AZURE_DEVOPS_EXT_PAT}` is not 5;
  - `git ls-remote https://dev.azure.com/aamnld/ccoe/_git/platform-iam` lists refs;
  - `git credential fill` for a `sbp-controltower` URL gets no password;
  - `ls -A ~/.azure/azuredevops ~/.azure-devops` is empty.
- [x] 6.4 Run `CLAUDE_DOCKER_OP_OPTIONAL=1 CLAUDE_DOCKER_ADO_APG_OP_REF='op://claude-docker/no-such-item/credential' cd-apg`. It must abort before launch, naming the variable. (b) In a normal `cd-apg` box, run `az devops configure --defaults organization=https://dev.azure.com/aamnld`, exit, then go to 6.5.
- [x] 6.5 Regression: start `cd-ct` with `CLAUDE_DOCKER_ADO_PROFILE=apg` added to the env file temporarily, then removed. Check:
  - tag `ado`;
  - `az devops configure --list` shows the SBP defaults;
  - SBP repos clone;
  - no new warnings.

## 7. Display label for the default box

- [x] 7.1 `run.sh`: tag `ado:<profile>`, else `ado:<CLAUDE_DOCKER_ADO_LABEL>`, else `ado`; env-file loader skips the label key; help text. **Proof:** the tag expression gives `ado:apg` / `ado:ct` / `ado` for profile+label / label only / neither; `bash -n run.sh`.
- [x] 7.2 `cd-ct`, `cd-ws13`: `export CLAUDE_DOCKER_ADO_LABEL=ct`. README line under "Named ADO profiles".
- [ ] 7.3 Relaunch `cd-ct` from WSL. Check: tag `ado:ct`; `az devops configure --list` unchanged.
