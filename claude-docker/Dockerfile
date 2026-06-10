# Pinned base image (digest pins all arches via the multi-arch index).
# Bump with: docker buildx imagetools inspect ubuntu:26.04 --format '{{.Manifest.Digest}}'
# Ubuntu (not Debian): only ubuntu:26.04 ships git ≥ 2.48 in its main archive,
# needed for the `extensions.relativeWorktrees` repo extension. Rationale and
# alternatives in openspec/changes/worktree-relative-paths/design.md.
FROM ubuntu:26.04@sha256:5e275723f82c67e387ba9e3c24baa0abdcb268917f276a0561c97bef9450d0b4

# pipefail propagates failures in RUN ... | ... — without this, a failed curl
# into tee/sha256sum silently succeeds and the build continues with bad data.
SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

# When bumping a version ARG, also refresh any paired sha256 ARG in the same commit.
# NODE_VERSION format is NodeSource's: <upstream>-1nodesource1.
# Bump with: curl -fsSL https://deb.nodesource.com/node_20.x/dists/nodistro/main/binary-amd64/Packages.gz | gunzip | grep -E '^(Package|Version):' | head -4
ARG NODE_VERSION=20.20.2-1nodesource1
ARG CLAUDE_CODE_VERSION=2.1.170
# Bump with: curl -fsSL https://downloads.claude.ai/claude-code-releases/${CLAUDE_CODE_VERSION}/manifest.json | jq -r '.platforms["linux-x64"].checksum, .platforms["linux-arm64"].checksum'
ARG CLAUDE_CODE_SHA256_X86_64=849e007277a0442ab27570d3e3d6d43787507946590e8dd1947e5a39b7081f9e
ARG CLAUDE_CODE_SHA256_AARCH64=1bb9d032440a75532f7dd4cafbc687f220aaf16c63eba17e192dfbec2f04bd25
# Policy: only pin versions ≥ 5 days old (loud supply-chain attacks usually get
# yanked within hours; the soak catches those, not quiet/targeted compromises).
ARG OPENSPEC_VERSION=1.3.0
ARG PNPM_VERSION=10.33.2
ARG GLAB_VERSION=1.92.1
ARG GLAB_DEB_SHA256_AMD64=18048e5cb2cbc92eb31d4190852c6da32f6713633cfefc7b3fe00c18806c4f53
ARG GLAB_DEB_SHA256_ARM64=f12a5e5e820b4c0b2803de4136884a90a64918bc3c7fd309f8c5a3ca9455fa8b
ARG AWSCLI_VERSION=2.34.31
ARG AWSCLI_SHA256_X86_64=d1540db414d48650c87cea7e2b585368b864d2be5fc4034f9af3b1e3dc2f678a
ARG AWSCLI_SHA256_AARCH64=932ff651397d5c56f78987fcdf736dfc62c2a32ed2c0e9c9ae96e9a7ff1e85ea
ARG UV_VERSION=0.11.8
ARG UV_SHA256_X86_64=56dd1b66701ecb62fe896abb919444e4b83c5e8645cca953e6ddd496ff8a0feb
ARG UV_SHA256_AARCH64=eee8dd658d20e5ac85fec9c2326b6cbc9d83a1eef09ef07433e58698ac849591
ARG TFENV_VERSION=3.0.0
ARG TFENV_SHA256=463132e45a211fa3faf85e62fdfaa9bb746343ff1954ccbad91cae743df3b648
ARG TOFUENV_VERSION=1.0.7
ARG TOFUENV_SHA256=047c6a01a0d4c7ded2cf126ae1e891bb3479b2544ec2d2f0d3951de2d08f6c7d
ARG ANDROID_CMDLINE_TOOLS_VERSION=11076708
ARG ANDROID_CMDLINE_TOOLS_SHA256=2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258
ARG GRADLE_VERSION=8.10
ARG GRADLE_SHA256=5b9c5eb3f9fc2c94abaea57d90bd78747ca117ddbbf96c859d3741181a12bf2a

# Make apt runnable under --cap-drop ALL at runtime. Two pieces:
#  1. APT::Sandbox::User "root" stops the http method from setgroups()→_apt
#     (needs CAP_SETGID, dropped at runtime).
#  2. chown archives/partial to root so apt can write it without
#     CAP_DAC_OVERRIDE/CAP_FOWNER — Ubuntu ships it as _apt:root 0700.
#     lists/partial doesn't need chowning: apt re-creates it as root at
#     runtime now that sandbox user is root.
# Safe here: the container itself is the security boundary, not apt's
# internal user split.
RUN echo 'APT::Sandbox::User "root";' > /etc/apt/apt.conf.d/10no-sandbox \
 && chown root:root /var/cache/apt/archives/partial

# NodeSource ships Node 20 LTS pinned to upstream releases — Ubuntu's archive
# `nodejs` tracks an older minor and isn't LTS-pinned. `nodistro` is
# NodeSource's distro-independent codename (works on any Debian/Ubuntu).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
 && install -d -m 0755 /etc/apt/keyrings \
 && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
 && chmod go+r /etc/apt/keyrings/nodesource.gpg \
 && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      "nodejs=${NODE_VERSION}" \
      git \
      tmux \
      ncurses-term \
      jq \
      less \
      openssh-client \
      unzip \
 && rm -rf /var/lib/apt/lists/*

# GitHub CLI (keyring fetched at build; TODO: commit the keyring to the repo)
RUN install -d -m 0755 /etc/apt/keyrings \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
 && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

# GitLab CLI (glab) — pinned version + sha256 verify
RUN ARCH=$(dpkg --print-architecture); \
    case "$ARCH" in \
      amd64) SHA="${GLAB_DEB_SHA256_AMD64}" ;; \
      arm64) SHA="${GLAB_DEB_SHA256_ARM64}" ;; \
      *) echo "Unsupported arch for glab: $ARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://gitlab.com/gitlab-org/cli/-/releases/v${GLAB_VERSION}/downloads/glab_${GLAB_VERSION}_linux_${ARCH}.deb" \
      -o /tmp/glab.deb \
 && echo "${SHA}  /tmp/glab.deb" | sha256sum -c - \
 && apt-get install -y --no-install-recommends /tmp/glab.deb \
 && rm /tmp/glab.deb

# AWS CLI v2 — pinned version + sha256 verify
RUN set -e; ARCH=$(uname -m); \
    case "$ARCH" in \
      x86_64)  SHA="${AWSCLI_SHA256_X86_64}" ;; \
      aarch64) SHA="${AWSCLI_SHA256_AARCH64}" ;; \
      *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}-${AWSCLI_VERSION}.zip" -o /tmp/awscli.zip \
 && echo "${SHA}  /tmp/awscli.zip" | sha256sum -c - \
 && unzip -q /tmp/awscli.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscli.zip

# uv (Astral) — pinned version + sha256 verify; uvx ships in the same archive.
# gnu variant: ubuntu is glibc; musl would silently fail at runtime.
# Hash pinned in ARG (not fetched from .sha256 sidecar) so a CDN swap is caught
# at build time — same trust model as the AWS CLI block above.
RUN set -e; ARCH=$(uname -m); \
    case "$ARCH" in \
      x86_64)  SHA="${UV_SHA256_X86_64}" ;; \
      aarch64) SHA="${UV_SHA256_AARCH64}" ;; \
      *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${ARCH}-unknown-linux-gnu.tar.gz" \
      -o /tmp/uv.tar.gz \
 && echo "${SHA}  /tmp/uv.tar.gz" | sha256sum -c - \
 && mkdir -p /tmp/uv \
 && tar -xzf /tmp/uv.tar.gz -C /tmp/uv \
 && install -m 0755 "/tmp/uv/uv-${ARCH}-unknown-linux-gnu/uv" /usr/local/bin/uv \
 && install -m 0755 "/tmp/uv/uv-${ARCH}-unknown-linux-gnu/uvx" /usr/local/bin/uvx \
 && rm -rf /tmp/uv /tmp/uv.tar.gz

# claude-code — native binary, Anthropic's recommended install path.
# Replicates the download+verify steps of claude.ai/install.sh without
# running the binary's `install` bootstrap. Manifest at
# downloads.claude.ai/.../<ver>/manifest.json carries per-platform sha256s;
# refresh both SHA256 ARGs in the same commit as the version bump. Ubuntu
# base is glibc, so we use linux-x64 / linux-arm64 (not the -musl variants).
#
# Installed under /opt so it survives the claude-code-root named volume
# masking /root at runtime (same rationale as tfenv/gradle/tofuenv). The
# native binary self-checks for itself at /root/.local/bin/claude (the
# launcher path it would normally create via `claude install`) — wiring
# that symlink up in the image's /root would be masked on every bump, so
# the entrypoint creates it at container start instead.
RUN set -e; ARCH=$(uname -m); \
    case "$ARCH" in \
      x86_64)  PLATFORM=linux-x64;   SHA="${CLAUDE_CODE_SHA256_X86_64}" ;; \
      aarch64) PLATFORM=linux-arm64; SHA="${CLAUDE_CODE_SHA256_AARCH64}" ;; \
      *) echo "Unsupported arch for claude-code: $ARCH" >&2; exit 1 ;; \
    esac; \
    mkdir -p /opt/claude-code \
 && curl -fsSL "https://downloads.claude.ai/claude-code-releases/${CLAUDE_CODE_VERSION}/${PLATFORM}/claude" \
      -o /opt/claude-code/claude \
 && echo "${SHA}  /opt/claude-code/claude" | sha256sum -c - \
 && chmod 0755 /opt/claude-code/claude \
 && ln -s /opt/claude-code/claude /usr/local/bin/claude

# npm-backed CLIs — pinned versions. Trust = npm's signed dist.integrity;
# run `npm audit signatures <pkg>@<ver>` when bumping.
# --ignore-scripts blocks lifecycle hooks for every package + transitive dep
# (hard security boundary, kept on). claude-code itself is no longer here:
# it ships as a native binary above, downloaded straight from Anthropic with
# a pinned sha256 — the npm route was a wrapper around the same binary.
RUN npm install -g --ignore-scripts \
      "@fission-ai/openspec@${OPENSPEC_VERSION}" \
      "pnpm@${PNPM_VERSION}"

# tfenv — pure-bash terraform version manager. Arch-independent (just
# bash scripts), so a single sha256 covers amd64 and arm64. We deliberately
# ship NO terraform binary; the project's `.terraform-version` (or an
# interactive `tfenv install <v>`) fetches the right version from
# releases.hashicorp.com at runtime, in the same runtime-fetch class as
# `pnpm dlx`/`uvx`. Installed under /opt (not /root) so image-level
# version bumps aren't shadowed by the claude-code-root named volume.
# Placed after the heavier npm install so a tfenv version bump doesn't
# invalidate that layer's cache (tfenv pins move far less often than the
# claude-code/openspec/pnpm pins above).
RUN curl -fsSL "https://github.com/tfutils/tfenv/archive/refs/tags/v${TFENV_VERSION}.tar.gz" \
      -o /tmp/tfenv.tar.gz \
 && echo "${TFENV_SHA256}  /tmp/tfenv.tar.gz" | sha256sum -c - \
 && mkdir -p /opt/tfenv \
 && tar -xzf /tmp/tfenv.tar.gz -C /opt/tfenv --strip-components=1 \
 && ln -s /opt/tfenv/bin/tfenv /usr/local/bin/tfenv \
 && ln -s /opt/tfenv/bin/terraform /usr/local/bin/terraform \
 && rm /tmp/tfenv.tar.gz

# tofuenv — OpenTofu version manager. Same rationale as tfenv above:
# pure-bash, arch-independent, ship NO tofu binary version (projects pin
# their own via .opentofu-version). Installed under /opt for the same
# upgrade-cleanliness reason — anything under /root would be frozen by the
# claude-code-root named volume on first run.
RUN curl -fsSL "https://github.com/tofuutils/tofuenv/archive/refs/tags/v${TOFUENV_VERSION}.tar.gz" \
      -o /tmp/tofuenv.tar.gz \
 && echo "${TOFUENV_SHA256}  /tmp/tofuenv.tar.gz" | sha256sum -c - \
 && mkdir -p /opt/tofuenv \
 && tar -xzf /tmp/tofuenv.tar.gz -C /opt/tofuenv --strip-components=1 \
 && ln -s /opt/tofuenv/bin/tofuenv /usr/local/bin/tofuenv \
 && ln -s /opt/tofuenv/bin/tofu /usr/local/bin/tofu \
 && rm /tmp/tofuenv.tar.gz

# Put /root/.local/bin on PATH so user-space installs land on PATH for every
# process in the container — including non-interactive `bash -c` subprocesses
# spawned by Claude's Bash tool, which do NOT source /root/.bashrc. Files under
# /root/.local survive across runs via the claude-code-root named volume, so
# `uv tool install <pkg>` (or `pipx install <pkg>`) inside a container becomes
# a persistent user-space install.
ENV PATH=/root/.local/bin:$PATH

# Azure CLI — Microsoft's apt repo. Same trust model as the `gh` block above:
# keyring fetched at build, repo pinned by signed-by. No version pin (matches
# `gh`); MS publishes only the latest in this repo, so rebuilds track upstream.
# Suite is pinned to `noble` (Ubuntu 24.04 LTS) because MS does not yet ship a
# suite for `resolute` (26.04 dev branch); the noble package is glibc-compatible
# on 26.04 and is what MS's `aka.ms/InstallAzureCLIDeb` installer falls back to
# for unsupported releases. Bump the AZ_DIST suite when MS adds a 26.04 suite.
# Why baked in (not `uv tool install azure-cli`): PyPI's azure-cli is frozen at
# 2.0.67 (2018); MS only ships current `az` via apt/yum/MSI. `--ado` controls
# credential forwarding (AZURE_DEVOPS_EXT_PAT); `az` itself is always present
# for parity with `aws`/`gh`/`glab`.
ARG AZ_DIST=noble
RUN install -d -m 0755 /etc/apt/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
 && chmod go+r /etc/apt/keyrings/microsoft.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ ${AZ_DIST} main" \
      > /etc/apt/sources.list.d/azure-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends azure-cli \
 && rm -rf /var/lib/apt/lists/*

# OpenJDK 17 (headless) — Android Gradle Plugin 8.x requires JDK 17. Headless
# is sufficient: no AWT/Swing in a CLI build. Same apt trust model as the
# Ubuntu base; no third-party repo.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
 && rm -rf /var/lib/apt/lists/*

# Gradle 8.10 — pinned. Projects pin their own version via
# gradle-wrapper.properties (the wrapper downloads on first run); the system
# gradle is for bootstrapping new projects (`gradle wrapper --gradle-version
# X.Y`) and for environments where wrapper download is blocked. Installed
# under /opt to survive the claude-code-root named volume (same rationale as
# tfenv/tofuenv above). Hash matches
# services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip.sha256.
RUN curl -fsSL "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" \
      -o /tmp/gradle.zip \
 && echo "${GRADLE_SHA256}  /tmp/gradle.zip" | sha256sum -c - \
 && unzip -q /tmp/gradle.zip -d /opt \
 && rm /tmp/gradle.zip

# Android SDK — cmdline-tools (sdkmanager) + platform-tools + Android 34
# platform + Build-Tools 34.0.0. Layout follows Google's
# `cmdline-tools/latest/` convention so sdkmanager finds itself; the zip
# unpacks into `cmdline-tools/`, which we rename to `latest`. Licenses
# accepted at build time so first-time `gradlew assembleDebug` doesn't
# prompt. Installed under /opt for the same upgrade-cleanliness reason as
# tfenv/gradle — anything under /root would be frozen by the
# claude-code-root named volume on first run.
#
# Platform + Build-Tools versions track Android API level; bump them in
# step. Three SDK packages cost ~500 MB image-side; that's the price of
# building Android locally without an Android Studio install. Gradle
# dependency cache (~/.gradle) is per-project and lives in the
# claude-code-root named volume, so it persists across container runs.
#
# Licenses are accepted via `printf 'y\n%.0s' $(seq 1 50)`, NOT `yes |`:
# under the Dockerfile's `SHELL [..., -eo, pipefail]`, `yes` getting
# SIGPIPE when sdkmanager closes stdin yields exit 141 and fails the
# RUN. printf streams a fixed number of acks and exits clean. 50 covers
# the current ~6 EULAs with headroom; bump if a future SDK adds more.
ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk
RUN curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_CMDLINE_TOOLS_VERSION}_latest.zip" \
      -o /tmp/cmdline-tools.zip \
 && echo "${ANDROID_CMDLINE_TOOLS_SHA256}  /tmp/cmdline-tools.zip" | sha256sum -c - \
 && mkdir -p "${ANDROID_HOME}/cmdline-tools" \
 && unzip -q /tmp/cmdline-tools.zip -d "${ANDROID_HOME}/cmdline-tools" \
 && mv "${ANDROID_HOME}/cmdline-tools/cmdline-tools" "${ANDROID_HOME}/cmdline-tools/latest" \
 && rm /tmp/cmdline-tools.zip \
 && printf 'y\n%.0s' $(seq 1 50) | "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" --licenses > /dev/null \
 && "${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager" \
      "platform-tools" \
      "platforms;android-34" \
      "build-tools;34.0.0" > /dev/null

ENV PATH=${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:/opt/gradle-${GRADLE_VERSION}/bin:${PATH}

# Plain `tmux` mode swallows Shift+Enter so Claude's prompt sees only Enter,
# forcing users to type `\` for a literal newline. `always` is required
# (not `on`) because Claude does not send the kitty activation request that
# `on` waits for — see claude-code#26629. /etc/tmux.conf, not
# /root/.tmux.conf, because /root is masked by the claude-code-root named
# volume at runtime. Harmless under tmux -CC: iTerm2 control mode bypasses
# tmux's input layer. Placed after npm install so edits don't invalidate
# the heavy AWS CLI / uv / glab / npm download layers above.
RUN cat > /etc/tmux.conf <<'EOF'
set -s extended-keys always
set -as terminal-features "*:extkeys"
EOF

# claude-docker-entrypoint: translates forwarded credential tokens into
# system-level `git insteadOf` rewrites at container start, so in-container
# `git` can clone private HTTPS repos against hosts the matching --gh/--glab
# flag is already authorising. Writes /etc/gitconfig (image-layer overlay,
# discarded on `docker run --rm` exit) — never the named volume's /root.
# See openspec/changes/add-git-insteadof/design.md.
# Placed after the tmux conf so edits here don't invalidate heavier
# upstream layers (apt/npm/glab/aws/uv/tfenv).
COPY entrypoint.sh /usr/local/bin/claude-docker-entrypoint
RUN chmod +x /usr/local/bin/claude-docker-entrypoint

# DISABLE_AUTOUPDATER=1 keeps the pinned CLAUDE_CODE_VERSION authoritative —
# without it, claude auto-replaces itself at runtime, defeating the
# --ignore-scripts supply-chain pinning above. Bump the image to upgrade.
ENV CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 \
    DISABLE_AUTOUPDATER=1 \
    IS_SANDBOX=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Container runs as root by design: IS_SANDBOX=1 + --cap-drop ALL + no-new-privileges
# make the container itself the security boundary. Do not add a USER directive
# without reworking the host-config bind-mount layout.

WORKDIR /workspaces

ENTRYPOINT ["/usr/local/bin/claude-docker-entrypoint"]
CMD ["claude"]
