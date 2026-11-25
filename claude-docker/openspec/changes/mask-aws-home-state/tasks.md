<!-- plan version: v1 -->
## 1. Mask

- [x] 1.1 `run.sh` mask block: add `--tmpfs /home/claude/.aws:$TMPFS_USER_OPTS`, unconditional (non-ephemeral). Comment why, next to the ADO mask. Proof: `bash -n run.sh`.
- [x] 1.2 `run.sh` `--aws` block comment and `entrypoint.sh` comment: say the credentials file lands on the tmpfs, not the volume.
- [x] 1.3 Spec delta in `specs/external-cli-tools/spec.md`.

## 2. Hook

- [x] 2.1 `deny-secret-reads.py`: add the ADO PAT path to `SECRET_SUFFIXES`; deny `git credential fill` and `git credential-store get`.
- [x] 2.2 Tests for both in `test_deny_secret_reads.py`, plus allow cases (`git credential approve`, `git config credential.helper`), which print no secret. Proof: `python3 -m unittest test_deny_secret_reads`.

## 3. Host checks (owner)

- [x] 3.1 Rebuild not needed (`~/.aws` is already pre-created in the Dockerfile). Launch a box without `--aws`: `ls -A ~/.aws` is empty and `findmnt /home/claude/.aws` shows tmpfs.
- [x] 3.2 Launch a box with `--aws`: `findmnt` shows the config/sso binds over the tmpfs (`cd-cis`). The `aws sts get-caller-identity --profile aegon` check was dropped: the Aegon account is obsolete and its key revoked.
- [ ] 3.3 Re-sync the installed hook. Boxes copy `hooks/` from the run.sh checkout at launch (`run.sh` wrapper-shipped hooks), so only the Windows host copy wired in the host `settings.json` needs it.
