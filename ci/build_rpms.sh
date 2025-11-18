#! /bin/bash -e

# Build RPMs for a given package using mock in a containerized environment.
#
# This script:
# - Builds the RPM using mock in the upstream RPM Build Pipeline container
# - Outputs both binary and source RPMs to a temporary results directory
#
# Usage: ./ci/build_rpms.sh PACKAGE_NAME
#   PACKAGE_NAME - Name of the package directory in rpms/
#
# The built RPMs can be found in: /tmp/konflux-build-PACKAGE_NAME-*/results/
#
# Note: This performs a non-hermetic package build in the same container
# environment as used by Konflux, but is not a drop-in replacement for the
# full Tekton pipeline.
#
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RPM_DIR=${SCRIPT_DIR}/../rpms

image=quay.io/redhat-user-workloads/rpm-build-pipeline-tenant/environment:latest@sha256:56bde7a1040650bc14ee927534426a52d88de30d588048c6a08be7a8758372cb
arch=x86_64

package_name=$1
test -n "${package_name}" || exit 1

workdir=$(mktemp -d "/tmp/konflux-build-${package_name}-XXXXXXXX")

cd "${workdir}"
mkdir results
mkdir config

# Allow mockbuilder (group mock) to read config and write results
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "results"
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "config"

# prepare mock config
sed "s|@ARCH@|${arch}|" "${SCRIPT_DIR}/../mock/mock.cfg" > "${workdir}/config/mock.cfg"

podman run --rm -ti --privileged --init \
    --pids-limit=16384 \
    -u mockbuilder \
    -v "${workdir}/results:/results:z" \
    -v "${workdir}/config:/config:z" \
    -v "${RPM_DIR}/${package_name}:/source:z" \
    "${image}" \
mock -r /config/mock.cfg \
     --spec "/source/${package_name}.spec" \
     --sources /source \
     --resultdir /results \

echo "RPMs:"
ls "${workdir}"/results/*.rpm
