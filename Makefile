PULL ?= newer
PODMAN_RUN = podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):/src:z -w /src -e XARGS_PARALLEL_JOBS
PODMAN_IMAGE = quay.io/hummingbird-ci/gitlab-ci:latest

.PHONY: delete-konflux-comments
delete-konflux-comments:
	podman run -it --rm -e GITLAB_TOKENS='{"gitlab.com":"COM_GITLAB_TOKEN"}' -e COM_GITLAB_TOKEN -v $(PWD):/src:z quay.io/cki/cki-tools:production /src/ci/delete_konflux_comments.py $(ARGS)


.PHONY: check-host check
check-host:
	git ls-files -z 'ci/*.sh' | xargs -0 shellcheck --external-sources --enable=all
	git ls-files -z 'ci/*.py' | xargs -0 -r ruff check
	git ls-files -z 'ci/*.py' | xargs -0 -r mypy
	if command -v pytest > /dev/null; then \
	  pytest -v; \
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
