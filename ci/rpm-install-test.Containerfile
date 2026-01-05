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
ARG LOCAL_REPO=""

FROM quay.io/hummingbird-ci/builder:latest-hatchling AS builder
ARG NEWROOT
ARG DNF_CACHE
ARG DNF_FLAGS
ARG LOCAL_REPO

# Create the new root and cache directories
RUN mkdir -p ${NEWROOT} ${DNF_CACHE}

# Import the fedora GPG key
RUN rpmkeys --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-rawhide-primary --root "${NEWROOT}"

# Copy the RPM to test
COPY test.rpm /tmp/test.rpm

# Configure Rawhide repository for dependency resolution until our hatchling repo is complete
RUN mkdir -p /etc/yum.repos.d/ && \
    cat <<EOF > /etc/yum.repos.d/rawhide.repo
[rawhide]
name=Fedora - Rawhide - Developmental packages for the next Fedora release
# Route through S3 cache for RPM caching; repodata passes through transparently
baseurl=https://koji-s3-cache.hummingbird-project.io/download-ib01.fedoraproject.org/pub/fedora/linux/development/rawhide/Everything/\$basearch/os/
enabled=1
priority=99
countme=1
metadata_expire=6h
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-rawhide-$basearch
skip_if_unavailable=False
EOF

# Copy local repository if present and configure it (only if LOCAL_REPO is set)
COPY local-repo /tmp/local-repo/
RUN <<EOF
if [ -n "${LOCAL_REPO}" ]; then
    mkdir -p /etc/yum.repos.d/
    cat <<EOT >> /etc/yum.repos.d/local.repo
[local-repo]
name=Local Repository
baseurl=file:///tmp/local-repo
enabled=1
gpgcheck=0
EOT
fi
EOF

# Install rpm CLI for validation
RUN dnf-installroot ${NEWROOT} ${DNF_FLAGS} install rpm

# Install the test RPM (will upgrade rpm if test RPM is the rpm package)
RUN dnf-installroot ${NEWROOT} ${DNF_FLAGS} install /tmp/test.rpm

# Verify the package was installed in the new root
RUN rpm --root ${NEWROOT} -qa | grep -q . || { echo "Error: No packages installed in ${NEWROOT}"; exit 1; }

# Drop any cache; source of irreproducibility.
# Also, some of our containers ship systemd for now, which creates a unique machine ID; nuke that.
RUN rm -rf \
      ${NEWROOT}/usr/share/licenses \
      ${NEWROOT}/usr/share/locale \
      ${NEWROOT}/var/cache/* \
      ${NEWROOT}/etc/machine-id

FROM scratch
ARG NEWROOT
COPY --from=builder ${NEWROOT} /
