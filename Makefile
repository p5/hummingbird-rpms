PULL ?= newer
PODMAN_RUN = podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):/src:z -w /src -e XARGS_PARALLEL_JOBS
PODMAN_IMAGE = quay.io/hummingbird-ci/gitlab-ci:latest

.PHONY: delete-konflux-comments
delete-konflux-comments:
	podman run -it --rm -e GITLAB_TOKENS='{"gitlab.com":"COM_GITLAB_TOKEN"}' -e COM_GITLAB_TOKEN -v $(PWD):/src:z quay.io/cki/cki-tools:production /src/ci/delete_konflux_comments.py $(ARGS)
