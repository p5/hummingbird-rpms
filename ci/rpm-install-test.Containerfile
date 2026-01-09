ARG NEWROOT=/new-root-fs
ARG DNF_CACHE=/tmp/dnf-cache
ARG DNF_FLAGS="-y \
      --use-host-config \
      --nodocs \
      --setopt=install_weak_deps=False \
      --setopt=cachedir=${DNF_CACHE} \
      --setopt=system_cachedir=${DNF_CACHE} \
      --setopt=logdir=${DNF_CACHE} \
      --setopt=varsdir=${DNF_CACHE}"
ARG PACKAGE_NAME

FROM quay.io/hummingbird-ci/builder:latest-hatchling AS builder
ARG NEWROOT
ARG DNF_CACHE
ARG DNF_FLAGS
ARG PACKAGE_NAME

# Create the new root directory
RUN mkdir -p ${NEWROOT}

# Import the fedora GPG key
RUN rpmkeys --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-rawhide-primary --root "${NEWROOT}"

# Configure repositories
COPY repos/rawhide.repo repos/hummingbird.repo /etc/yum.repos.d/

# Copy and configure local repository (contains built RPMs to test)
COPY local-repo /tmp/local-repo/
RUN cat <<EOT >> /etc/yum.repos.d/local.repo
[local-repo]
name=Local Repository
baseurl=file:///tmp/local-repo
enabled=1
gpgcheck=0
priority=1
EOT

# Install filesystem first, then the test package.
# The local-repo has priority=1 to ensure it takes precedence over other repos.
# Dependencies may come from other repos (rawhide, hummingbird) as needed.
# Cache mount persists dnf downloads across builds for faster repeated runs.
RUN --mount=type=cache,target=/tmp/dnf-cache \
    dnf-installroot ${NEWROOT} ${DNF_FLAGS} install filesystem && \
    dnf-installroot ${NEWROOT} ${DNF_FLAGS} install ${PACKAGE_NAME}

# Verify the package was installed from local-repo
RUN install_repo=$(dnf --installroot=${NEWROOT} info --installed ${PACKAGE_NAME} 2>/dev/null | \
      grep "^From repo" | cut -d: -f2 | tr -d ' ') && \
    if [ "${install_repo}" != "local-repo" ]; then \
      echo "Error: Package '${PACKAGE_NAME}' was not installed from local-repo (got: ${install_repo:-unknown})"; \
      exit 1; \
    fi && \
    echo "Verified: ${PACKAGE_NAME} installed from local-repo"
