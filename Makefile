PWD_REALPATH := $(shell realpath .)
GIT_COMMON_DIR := $(shell git rev-parse --git-common-dir 2>/dev/null || echo "")
WORKTREE_MOUNT := $(shell [ -n "$(GIT_COMMON_DIR)" ] && [ "$(GIT_COMMON_DIR)" != ".git" ] && echo "-v $(GIT_COMMON_DIR):$(GIT_COMMON_DIR):z" || echo "")

PULL ?= newer
PODMAN_RUN = podman run --pull=$(PULL) --label io.hummingbird-project.makefile-container=true $(shell [ -t 0 ] && echo "-it" || echo "-i") --rm -u 0 -v $(PWD_REALPATH):$(PWD_REALPATH):z $(WORKTREE_MOUNT) -w $(PWD_REALPATH) -e XARGS_PARALLEL_JOBS -e GITLAB_TOKEN
PODMAN_IMAGE = quay.io/hummingbird-ci/gitlab-ci:latest


.PHONY: container
container:
	$(PODMAN_RUN) $(PODMAN_IMAGE) sh


.PHONY: delete-konflux-comments
delete-konflux-comments:
	podman run -it --rm -e GITLAB_TOKENS='{"gitlab.com":"COM_GITLAB_TOKEN"}' -e COM_GITLAB_TOKEN -v $(PWD):/src:z quay.io/cki/cki-tools:production /src/ci/delete_konflux_comments.py $(ARGS)


.PHONY: check-host check
check-host:
	git ls-files -z 'ci/*.sh' | xargs -0 shellcheck --external-sources --enable=all
	git ls-files -z 'ci/*.py' | xargs -0 -r ruff check
	git ls-files -z 'ci/*.py' | xargs -0 -r mypy
	if command -v pytest > /dev/null; then \
	  pytest -v test/; \
	else \
	  echo "pytest not installed, skipping tests"; \
	fi

check:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make check-host


.PHONY: generate-host generate
generate-host:
	ci/generate.sh $(ARGS)
generate:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make generate-host ARGS='$(ARGS)'


.PHONY: dist-git-host dist-git
dist-git-host:
	ci/dist_git.py $(ARGS)
dist-git:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make dist-git-host ARGS='$(ARGS)'
