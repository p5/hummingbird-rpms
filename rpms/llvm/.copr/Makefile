# See https://docs.pagure.org/copr.copr/user_documentation.html#make-srpm
# See for the --setopt option in the enabling of copr repo see:
# https://pagure.io/copr/copr/issue/184

COPR_USERNAME=$(shell rpm --eval %copr_username)
COPR_PROJECT=$(shell rpm --eval %copr_projectname)
YYYYMMDD=$(shell date +%Y%m%d)

required_packages=git tar xz curl fedpkg rpmautospec
outdir?=$(shell pwd)
spec?=llvm.spec

.PHONY: srpm
srpm:
	@echo "Check for required packages needed by snapshot-info.sh: $(required_packages)"
	rpm -q $(required_packages) || dnf install -y $(required_packages) --setopt=install_weak_deps=False

	@echo "Fetch information about today's snapshot"
	YYYYMMDD=$(YYYYMMDD) ./.copr/snapshot-info.sh > version.spec.inc

	@echo "Get sources"
	fedpkg --release rawhide sources --outdir $(shell pwd)

	@echo "Remove left-over llvm-project tarball and signature"
	rm -vf $(shell pwd)/llvm-project-*.tar.xz*

	@echo "Preprocess for rpmautospec"
	rpmautospec process-distgit $(spec) $(spec)

	@echo "Finally build SRPM"
	rpmbuild \
		--with=snapshot_build \
		--define "_srcrpmdir $(outdir)" \
		--define "_sourcedir $(shell pwd)" \
		--define "_disable_source_fetch 0" \
		-bs $(spec)
