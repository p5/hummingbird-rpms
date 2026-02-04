#!/usr/bin/env bash
set -euo pipefail

# Verify that each spec in rpms/*/*.spec has corresponding RPMs in the remote repos.
# By default, checks the public hummingbird repos for x86_64 and aarch64. A package
# is considered OK when present for x86_64 and for aarch64 (or as noarch).
#
# Environment/flags:
#   BASE_URL   - override the base x86_64 repo URL
#   --base-url URL  - same as BASE_URL
#   --only NAME,... - comma-separated list of package names to check (filter)
#   BASE_URL_AARCH64 - override the base aarch64 repo URL
#   ARCHES - comma-separated list of arches to require (default: x86_64,aarch64)
#
# Examples:
#   ./ci/verify_rpms_in_pulp.sh
#   BASE_URL=https://example/repo/x86_64 ./ci/verify_rpms_in_pulp.sh

BASE_URL_DEFAULT="https://packages.redhat.com/api/pulp-content/public-hummingbird/x86_64/"
BASE_URL="${BASE_URL:-${BASE_URL_DEFAULT}}"
BASE_URL_AARCH64_DEFAULT="https://packages.redhat.com/api/pulp-content/public-hummingbird/aarch64/"
BASE_URL_AARCH64="${BASE_URL_AARCH64:-${BASE_URL_AARCH64_DEFAULT}}"
ONLY_FILTER=""
HB_DEBUG="${HB_DEBUG:-0}"
DNF_TIMEOUT_SECS="${DNF_TIMEOUT_SECS:-8}"
ARCHES="${ARCHES:-x86_64,aarch64}"

dlog() {
	if [[ "${HB_DEBUG}" -eq 1 ]]; then
		# shellcheck disable=SC2145
		echo "DEBUG: $*" >&2
	fi
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--base-url)
			shift
			BASE_URL="${1:-${BASE_URL}}"
			;;
		--only)
			shift
			ONLY_FILTER="${1:-}"
			;;
		--debug)
			HB_DEBUG=1
			;;
		--arches)
			shift
			ARCHES="${1:-${ARCHES}}"
			;;
		*)
			echo "Unknown argument: $1" >&2
			exit 2
			;;
	esac
	shift
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
rpms_dir="${repo_root}/rpms"

dlog "BASE_URL=${BASE_URL}"
dlog "BASE_URL_AARCH64=${BASE_URL_AARCH64}"
dlog "ONLY_FILTER=${ONLY_FILTER}"
dlog "rpms_dir=${rpms_dir}"
dlog "DNF_TIMEOUT_SECS=${DNF_TIMEOUT_SECS}"
dlog "ARCHES=${ARCHES}"

# Return true (0) if the remote repo at $2 has a package named $1 for $3 arch
# Resolve base URL for a given arch
base_url_for_arch() {
	case "$1" in
		x86_64) printf '%s\n' "${BASE_URL}" ;;
		aarch64) printf '%s\n' "${BASE_URL_AARCH64}" ;;
		*) printf '%s\n' "" ;;
	esac
}

# Find one matching RPM for name+arch in base_url and print: "NEVRA<TAB>location"
# Returns 0 if found, 1 otherwise.
find_rpm_location() {
	local name="$1"
	local base_url="$2"
	local arch="$3"
	local repoid="hbcheck"
	local out
	# shellcheck disable=SC2086
	out="$(
		timeout "${DNF_TIMEOUT_SECS}s" dnf -q \
			--repofrompath "${repoid},${base_url}" \
			--repo "${repoid}" \
			repoquery --latest-limit 1 --qf '%{name}-%{version}-%{release}.%{arch}\t%{location}\n' "${name}.${arch}" 2>/dev/null
	)"
	# Always return success; callers check for non-empty output
	printf '%s\n' "${out}" | head -n1
	return 0
}

# Resolve spec Name using rpmspec
spec_name() {
	local spec="$1"
	local spec_dir
	spec_dir="$(dirname "${spec}")"
	# Query spec for the SRPM name macro; neutralize dist; set _sourcedir to spec dir
	# Use head -n1 to guard against multiple outputs (should not happen for %{NAME})
	rpmspec -q --qf '%{NAME}\n' \
		--define="dist %{nil}" \
		--define="_sourcedir ${spec_dir}" \
		--srpm "${spec}" | head -n1 | tr '[:upper:]' '[:lower:]'
}

# List binary package names produced by this spec (lowercased), excluding debuginfo/debugsource
list_binary_names() {
	local spec="$1"
	local spec_dir
	spec_dir="$(dirname "${spec}")"
	# Query all packages, then filter to only binary packages (ARCH != src)
	rpmspec -q --qf '%{NAME}\t%{ARCH}\n' \
		--define="dist %{nil}" \
		--define="_sourcedir ${spec_dir}" \
		"${spec}" | awk 'BEGIN{IGNORECASE=1} $2 != "" && tolower($2)!="src" { print tolower($1) }' | grep -Ev '(-debuginfo|-debugsource)$' | sort -u
}
filter_includes() {
	local name="$1"
	if [[ -z "${ONLY_FILTER}" ]]; then
		return 0
	fi
	local item
	IFS=',' read -r -a items <<< "${ONLY_FILTER}"
	for item in "${items[@]}"; do
		if [[ "${name}" == "${item}" ]]; then
			return 0
		fi
	done
	return 1
}

if [[ ! -d "${rpms_dir}" ]]; then
	echo "Could not find rpms directory at: ${rpms_dir}" >&2
	exit 2
fi

echo "Remote repo (x86_64): ${BASE_URL}"
echo "Remote repo (aarch64): ${BASE_URL_AARCH64}"
echo "Looking for x86_64 and aarch64 RPMs for spec files under: ${rpms_dir}"

if ! command -v dnf >/dev/null 2>&1; then
	echo "ERROR: dnf is required but not found in PATH." >&2
	exit 2
fi
echo "Using dnf repoquery only."

total=0
found=0
missing=0
declare -a missing_list=()

# Build the list of spec files first; preserve NULs and fail clearly if enumeration fails
spec_list_tmp="$(mktemp)"
trap 'rm -f "${spec_list_tmp}"' EXIT
if ! (find "${rpms_dir}" -mindepth 2 -maxdepth 2 -type f -name '*.spec' -print0 | sort -z > "${spec_list_tmp}"); then
	echo "ERROR: failed to enumerate spec files" >&2
	exit 2
fi
mapfile -d '' -t spec_files < "${spec_list_tmp}"
dlog "spec_files count=${#spec_files[@]}"

for spec in "${spec_files[@]}"; do
	# Prefer binary package list from rpmspec; fallback to SRPM name
	bin_text="$(list_binary_names "${spec}")"
	rc_list=$?
	if [[ ${rc_list} -ne 0 ]]; then
		bin_text=""
	fi
	mapfile -t bin_names <<< "${bin_text}"
	if [[ ${#bin_names[@]} -eq 0 ]]; then
		name="$(spec_name "${spec}")"
		if [[ -n "${name}" ]]; then
			bin_names=("${name}")
		fi
	fi
	if [[ ${#bin_names[@]} -eq 0 ]]; then
		echo "WARN: Could not parse Name: from spec ${spec}" >&2
		continue
	fi
	(( total+=1 ))
	dlog "Checking spec: ${spec}"
	spec_dname="$(basename "$(dirname "${spec}")")"
	dlog "Spec ${spec_dname} binaries: ${bin_names[*]}"

	# For this spec, require presence for required arches (any one binary per arch is sufficient; noarch accepted)
	IFS=',' read -r -a required_arches <<< "${ARCHES}"
	miss_arches=()
	for arch in "${required_arches[@]}"; do
		base_url="$(base_url_for_arch "${arch}")"
		if [[ -z "${base_url}" ]]; then
			dlog "Unknown arch '${arch}' requested; skipping"
			continue
		fi
		found_for_arch=0
		for pkg in "${bin_names[@]}"; do
			# shellcheck disable=SC2310
			if ! filter_includes "${pkg}"; then
				continue
			fi
			# Prefer exact arch, fallback to noarch in same repo
			match_line="$(find_rpm_location "${pkg}" "${base_url}" "${arch}")"
			if [[ -n "${match_line}" ]]; then rc_exact=0; else rc_exact=1; fi
			rc_noarch=1
			if [[ ${rc_exact} -ne 0 ]]; then
				match_line_noarch="$(find_rpm_location "${pkg}" "${base_url}" "noarch")"
				if [[ -n "${match_line_noarch}" ]]; then rc_noarch=0; else rc_noarch=1; fi
			fi
			if [[ ${rc_exact} -eq 0 || ${rc_noarch} -eq 0 ]]; then
				if [[ ${rc_exact} -eq 0 ]]; then
					nevr="$(printf '%s\n' "${match_line}" | awk -F'\t' '{print $1}')"
					loc="$(printf '%s\n' "${match_line}" | awk -F'\t' '{print $2}')"
					case "${loc}" in
						http://*|https://*) url="${loc}" ;;
						*) url="${base_url%/}/${loc#./}" ;;
					esac
					dlog "Satisfied arch ${arch} for spec ${spec_dname} with binary ${pkg} (exact match): ${nevr} @ ${url}"
				else
					nevr="$(printf '%s\n' "${match_line_noarch}" | awk -F'\t' '{print $1}')"
					loc="$(printf '%s\n' "${match_line_noarch}" | awk -F'\t' '{print $2}')"
					case "${loc}" in
						http://*|https://*) url="${loc}" ;;
						*) url="${base_url%/}/${loc#./}" ;;
					esac
					dlog "Satisfied arch ${arch} for spec ${spec_dname} with binary ${pkg} (noarch fallback): ${nevr} @ ${url}"
				fi
				found_for_arch=1
				break
			fi
		done
		if [[ ${found_for_arch} -ne 1 ]]; then
			dlog "No binary from spec ${spec_dname} found for required arch ${arch}"
			miss_arches+=("${arch}")
		fi
	done
	if [[ ${#miss_arches[@]} -eq 0 ]]; then
		echo "OK     ${spec_dname}"
		(( found+=1 ))
	else
		# Build per-binary specifics for the missing arches
		spec_missing_details=()
		for pkg in "${bin_names[@]}"; do
			# shellcheck disable=SC2310
			if ! filter_includes "${pkg}"; then
				continue
			fi
			pkg_miss=()
			for arch in "${miss_arches[@]}"; do
				base_url="$(base_url_for_arch "${arch}")"
				match_line_pkg="$(find_rpm_location "${pkg}" "${base_url}" "${arch}")"
				if [[ -n "${match_line_pkg}" ]]; then rc_exact_pkg=0; else rc_exact_pkg=1; fi
				match_line_pkg_noarch="$(find_rpm_location "${pkg}" "${base_url}" "noarch")"
				if [[ -n "${match_line_pkg_noarch}" ]]; then rc_noarch_pkg=0; else rc_noarch_pkg=1; fi
				if [[ ${rc_exact_pkg} -ne 0 && ${rc_noarch_pkg} -ne 0 ]]; then
					pkg_miss+=("${arch}")
				fi
			done
			if [[ ${#pkg_miss[@]} -gt 0 ]]; then
				spec_missing_details+=("${pkg}:[${pkg_miss[*]}]")
			fi
		done
		if [[ ${#spec_missing_details[@]} -gt 0 ]]; then
			echo "MISSING ${spec_dname} -> ${spec_missing_details[*]}"
		else
			echo "MISSING ${spec_dname} -> missing_arches:[${miss_arches[*]}]"
		fi
		missing_list+=("${spec_dname}")
		(( missing+=1 ))
	fi
done

echo
echo "Checked: ${total}  Found: ${found}  Missing: ${missing}"
if (( missing > 0 )); then
	printf 'Missing packages: %s\n' "${missing_list[*]}"
	echo
	echo "You can try to trigger RPM builds for missing packages by running:"
	for pkg in "${missing_list[@]}"; do
		echo "  kubectl annotate components/${pkg}-main build.appstudio.openshift.io/request=trigger-pac-build"
	done
fi

if (( missing > 0 )); then
	exit 1
fi

exit 0
