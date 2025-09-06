# Ensure that errors don't hide inside pipes
SHELL         = /bin/bash
.SHELLFLAGS   = -o pipefail -c

# VERSION could be set to more than one space-separated value, e.g. "5.3.2 5.3"
VERSION      ?= $(shell sed -E -n "/__version__/s/^(.*'([^']+)'.*)$$/\2/p" ./openmaptiles/__init__.py)
IMAGE_REPO   ?= openmaptiles
IMAGE_NAME   ?= $(IMAGE_REPO)/openmaptiles-tools
DOCKER_IMAGE ?= $(IMAGE_NAME):$(word 1,$(VERSION))
BUILD_DIR    ?= build

# Options to run with docker - ensure the container is destroyed on exit,
# runs as the current user rather than root (so that created files are not root-owned)
DOCKER_OPTS  ?= -i --rm -u $$(id -u $${USER}):$$(id -g $${USER})

# Optionally pass in extra parameters to the docker build command
DOCKER_BUILD_EXTRAS ?=

# https://github.com/openmaptiles/openmaptiles/pull/1497
# Support newer `docker compose` syntax in addition to `docker-compose`
ifeq (, $(shell which docker-compose))
  DOCKER_COMPOSE_COMMAND := docker compose
  $(info Using docker compose V2 (docker compose))
else
  DOCKER_COMPOSE_COMMAND := docker-compose
  $(info Using docker compose V1 (docker-compose))
endif

ifneq ($(strip $(NO_REFRESH)),)
  $(info Skipping docker image refresh)
else
  DOCKER_BUILD_EXTRAS := $(DOCKER_BUILD_EXTRAS) --pull
endif

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
	docker build $(DOCKER_BUILD_EXTRAS) \
		$(foreach ver, $(VERSION), --tag $(IMAGE_NAME):$(ver)) \
		.

.PHONY: build-generate-vectortiles
build-generate-vectortiles:
	docker build $(DOCKER_BUILD_EXTRAS) \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/generate-vectortiles:$(ver)) \
		docker/generate-vectortiles

.PHONY: build-postgis
build-postgis:
	docker build $(DOCKER_BUILD_EXTRAS) \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/postgis:$(ver)) \
		docker/postgis

.PHONY: build-import-data
build-import-data:
	docker build $(DOCKER_BUILD_EXTRAS) \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/import-data:$(ver)) \
		docker/import-data

.PHONY: build-postgis-preloaded
build-postgis-preloaded: build-postgis build-import-data
	docker build $(DOCKER_BUILD_EXTRAS) \
		--build-arg "OMT_TOOLS_VERSION=$(word 1,$(VERSION))" \
		$(foreach ver, $(VERSION), --tag $(IMAGE_REPO)/postgis-preloaded:$(ver)) \
		docker/postgis-preloaded

.PHONY: build-all-dockers
build-all-dockers: build-docker build-generate-vectortiles build-import-data build-postgis build-postgis-preloaded

.PHONY: run-python-tests
run-python-tests: build-docker
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Python unit tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@$(RUN_CMD) $(DOCKER_IMAGE)  bash -c \
		'cd /usr/src/app && \
		 if [ -d "tests/python" ]; then \
		   python -m flake8 openmaptiles tests/python `grep -rIzl "^#!.*python" bin`; \
		 else \
		   python -m flake8 openmaptiles `grep -rIzl "^#!.*python" bin`; \
		 fi && \
		 if [ -d "tests/python" ]; then \
		   cd tests/python && python -m unittest discover -p "test_*.py" 2>&1 | \
		   awk -v s="Ran 0 tests in" '\''$$0~s{print; print "\n*** No Python unit tests found, aborting"; exit(1)} 1'\''; \
		 else \
		   echo "No Python tests found, skipping"; \
		 fi'

.PHONY: build-sql-tests
build-sql-tests: prepare build-docker
	# Run postgis (latest) image, import all SQL tools/languages code, and run the tests
	# Make sure to cleanup before and after to make sure no volume stays behind
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Postgres SQL tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(DOCKER_COMPOSE_COMMAND) --file tests/sql/docker-compose.yml rm -f && \
	$(DOCKER_COMPOSE_COMMAND) --file tests/sql/docker-compose.yml up --wait-timeout 180 && \
	$(DOCKER_COMPOSE_COMMAND) --file tests/sql/docker-compose.yml rm -f

.PHONY: build-bin-tests
build-bin-tests: prepare build-docker
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running tools integration tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(RUN_CMD) -e "BUILD=/tileset/$(BUILD_DIR)" \
		-v "$(WORKDIR)/tests/cache:/usr/src/app/cache" \
		$(DOCKER_IMAGE) /tileset/tests/test-tools.sh

.PHONY: build-tests
build-tests: build-bin-tests build-sql-tests
	# Run all tests that generate test results in the build dir

.PHONY: bash
bash:
	$(RUN_CMD) -it $(DOCKER_IMAGE) bash
