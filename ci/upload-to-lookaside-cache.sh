#!/bin/bash
set -euo pipefail

# dist-git cache upload script
# Uploads a file to S3 with the correct dist-git path structure

usage() {
    cat <<EOF
Usage: $0 -f FILE -p PACKAGE [-n NAMESPACE] [-t HASHTYPE] [-b BUCKET]

Upload a file to the dist-git S3 cache.

Options:
    -f FILE       File to upload (required)
    -p PACKAGE    Package name (required)
    -n NAMESPACE  Namespace (default: rpms)
    -t HASHTYPE   Hash type: sha512, sha1, md5 (default: sha512)
    -b BUCKET     S3 bucket name (default: hummingbird-dist-git-cache-prod)
    -h            Show this help

Example:
    $0 -f tar-1.35.tar.xz -p tar
    $0 -f source.tar.gz -p mypackage -n modules -t sha256
EOF
    exit 1
}

# Check for required commands
if ! command -v aws &> /dev/null; then
    echo "Error: aws cli is not installed"
    exit 1
fi

# Defaults
NAMESPACE="rpms"
HASHTYPE="sha512"
BUCKET="arr-hummingbird-prod-dist-git-cache"
FILE=""
PACKAGE=""

# Parse arguments
while getopts "f:p:n:t:b:h" opt; do
    case ${opt} in
        f) FILE="${OPTARG}" ;;
        p) PACKAGE="${OPTARG}" ;;
        n) NAMESPACE="${OPTARG}" ;;
        t) HASHTYPE="${OPTARG}" ;;
        b) BUCKET="${OPTARG}" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required arguments
if [[ -z "${FILE}" ]]; then
    echo "Error: File (-f) is required"
    usage
fi

if [[ -z "${PACKAGE}" ]]; then
    echo "Error: Package (-p) is required"
    usage
fi

if [[ ! -f "${FILE}" ]]; then
    echo "Error: File not found: ${FILE}"
    exit 1
fi

# Get filename from path
FILENAME=$(basename "${FILE}")

# Calculate hash
case "${HASHTYPE}" in
    sha512) HASH=$(sha512sum "${FILE}" | awk '{print $1}') ;;
    sha256) HASH=$(sha256sum "${FILE}" | awk '{print $1}') ;;
    sha1)   HASH=$(sha1sum "${FILE}" | awk '{print $1}') ;;
    md5)    HASH=$(md5sum "${FILE}" | awk '{print $1}') ;;
    *)
        echo "Error: Invalid hash type: ${HASHTYPE}"
        echo "Supported: sha512, sha256, sha1, md5"
        exit 1
        ;;
esac

# Build S3 key: {namespace}/{package}/{filename}/{hashType}/{hash}/{filename}
# Note: hashtype must be lowercase to match dist-git-client expectations
S3_KEY="${NAMESPACE}/${PACKAGE}/${FILENAME}/${HASHTYPE}/${HASH}/${FILENAME}"

echo "Uploading to dist-git cache..."
echo "  File:      ${FILE}"
echo "  Package:   ${PACKAGE}"
echo "  Namespace: ${NAMESPACE}"
echo "  Hash type: ${HASHTYPE}"
echo "  Hash:      ${HASH}"
echo "  S3 key:    ${S3_KEY}"
echo ""

# Upload to S3
aws s3 cp "${FILE}" "s3://${BUCKET}/${S3_KEY}"

echo ""
echo "Upload complete!"
echo ""
echo "Sources file entry:"
echo "${HASHTYPE^^} (${FILENAME}) = ${HASH}"
