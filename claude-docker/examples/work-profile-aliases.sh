# claude-docker work-profile launchers
# -----------------------------------------------------------------------------
# Each profile forwards ONLY the credentials that kind of work needs, so a
# prompt-injected repo can exfiltrate a narrower set of tokens (see the
# "Minimizing credential blast radius" section in the README). One flag = one
# credential in the blast radius; the kitchen-sink launch carries them all.
#
# Install (host):
#   cp claude-docker/examples/work-profile-aliases.sh ~/.config/claude-docker/aliases.sh
#   # then in ~/.bashrc:
#   [ -f ~/.config/claude-docker/aliases.sh ] && . ~/.config/claude-docker/aliases.sh
#
# Usage:
#   ccis                 # launch a CIS session
#   ccis -- --resume     # append claude flags after the profile
#   ccisr                # narrowest CIS session (GitLab only, no cloud creds)
#
# Switching work does NOT require closing the current container: open a new
# terminal and run another profile. Concurrent containers are supported
# (worktree-guard handles shared checkouts), so you never trade a running
# session to change flags.
#
# Mounts are scoped per profile (a second blast-radius lever): a session can
# only reach what's mounted. Widen to "$DEV" if you genuinely need cross-project
# reach in one session.

DEV=/mnt/c/dev

# Common base: yolo + Claude auth. Everything else is per-profile.
_ccbase() { claude-docker --yolo --claude-auth "$@"; }

# CIS platform + multi-tenant deploy (GitLab repo + AWS ASR/Aegon + tofu).
# tools/ mounted alongside per the CIS convention (read-only via launcher pin).
ccis()    { _ccbase --glab --aws --tofu "$DEV/sbp/cis/" "$DEV/tools/" "$@"; }

# CIS code-only, narrowest: just the GitLab repo, no cloud credentials at all.
ccisr()   { _ccbase --glab "$DEV/sbp/cis/" "$@"; }

# Control Tower (.NET / Azure DevOps).
cct()     { _ccbase --ado "$DEV/sbp/ct/" "$@"; }

# Personal / GitHub work (myEntryPoint, laslo).
cgh()     { _ccbase --gh "$DEV" "$@"; }

# Editing claude-docker itself: GitHub + writable launcher dir.
cdocker() { _ccbase --gh --tools "$DEV/tools/claude-shared/" "$@"; }

# Everything — the old kitchen-sink default. Widest blast radius; use only when
# a single session genuinely spans GitLab + GitHub + Azure DevOps + AWS.
cfull()   { _ccbase --tofu --glab --aws --gh --ado --tools "$DEV" "$@"; }
