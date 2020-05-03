# Ensure that errors don't hide inside pipes
SHELL         = /bin/bash
.SHELLFLAGS   = -o pipefail -c

# VERSION could be set to more than one space-separated value, e.g. "5.3.2 5.3"
VERSION      ?= $(shell grep __version__ ./openmaptiles/__init__.py | sed -E 's/^(.*"([^"]+)".*|.*)$$/\2/')
IMAGE_REPO   ?= openmaptiles
IMAGE_NAME   ?= $(IMAGE_REPO)/openmaptiles-tools
DOCKER_IMAGE ?= $(IMAGE_NAME):$(word 1,$(VERSION))
BUILD_DIR    ?= build

# Options to run with docker - ensure the container is destroyed on exit,
# runs as the current user rather than root (so that created files are not root-owned)
DOCKER_OPTS  ?= -i --rm -u $$(id -u $${USER}):$$(id -g $${USER})

# Current dir is shared with the docker, allowing scripts to write to the dir as a current user
WORKDIR      ?= $$( pwd -P )
RUN_CMD := docker run ${DOCKER_OPTS} -v "$(WORKDIR):/tileset"

DIFF_CMD := diff --brief --recursive --new-file
EXPECTED_DIR := tests/expected

# Export image name so that tests/sql/docker-compose.yml can use it
export DOCKER_IMAGE

.PHONY: test
test: clean run-python-tests build-tests
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Comparing built results with the expected ones"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(DIFF_CMD) "$(BUILD_DIR)" "$(EXPECTED_DIR)"
	@echo "<<<<<<<<<<<<<<<<<<<<< SUCCESS <<<<<<<<<<<<<<<<<<<<<"

.PHONY: clean
clean:
	rm -rf "$(BUILD_DIR)"

# Delete dir with the expected test results and rebuild them
.PHONY: rebuild-expected
rebuild-expected: clean build-tests
	rm -rf "$(EXPECTED_DIR)"
	mkdir -p "$(EXPECTED_DIR)"
	mv "$(BUILD_DIR)"/* "$(EXPECTED_DIR)/"

# Create build dir, and allow modification from within docker under non-root user
.PHONY: prepare
prepare:
	mkdir -p "$(BUILD_DIR)"
	chmod 777 "$(BUILD_DIR)"

.PHONY: build-docker
build-docker:
	docker build \
		$(foreach ver, $(VERSION), --tag $(IMAGE_NAME):$(ver)) \
		.

.PHONY: build-generate-vectortiles
build-generate-vectortiles:
	docker build \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/generate-vectortiles:$(ver)) \
		docker/generate-vectortiles

.PHONY: build-postgis
build-postgis:
	docker build \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/postgis:$(ver)) \
		docker/postgis

.PHONY: build-import-data
build-import-data:
	docker build \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/import-data:$(ver)) \
		docker/import-data

# This step assumes the dependent docker images have already been built
.PHONY: build-postgis-preloaded-nodep
build-postgis-preloaded-nodep:
	docker build \
		--build-arg "OMT_TOOLS_VERSION=$(word 1,$(VERSION))" \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/postgis-preloaded:$(ver)) \
		docker/postgis-preloaded

.PHONY: build-postgis-preloaded
build-postgis-preloaded: build-postgis build-import-data build-postgis-preloaded-nodep

.PHONY: build-all-dockers
build-all-dockers: build-docker build-generate-vectortiles build-import-data build-postgis build-postgis-preloaded

.PHONY: run-python-tests
run-python-tests: build-docker
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Python unit tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(RUN_CMD) $(DOCKER_IMAGE) python -m unittest discover 2>&1 | \
		awk -v s="Ran 0 tests in" '$$0~s{print; print "\n*** No Python unit tests found, aborting"; exit(1)} 1'

.PHONY: build-sql-tests
build-sql-tests: prepare build-docker
	# Run postgis (latest) image, import all SQL tools/languages code, and run the tests
	# Make sure to cleanup before and after to make sure no volume stays behind
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Postgres SQL tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	docker-compose --file tests/sql/docker-compose.yml rm -f && \
	timeout 60 docker-compose --file tests/sql/docker-compose.yml up --abort-on-container-exit && \
	docker-compose --file tests/sql/docker-compose.yml rm -f

.PHONY: build-bin-tests
build-bin-tests: prepare build-docker
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running tools integration tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(RUN_CMD) -e "BUILD=/tileset/$(BUILD_DIR)" \
		-v "$(WORKDIR)/tests/cache:/usr/src/app/cache" \
		$(DOCKER_IMAGE) tests/test-tools.sh

.PHONY: build-tests
build-tests: build-bin-tests build-sql-tests
	# Run all tests that generate test results in the build dir
