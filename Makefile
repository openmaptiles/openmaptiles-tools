VERSION      ?= $(shell grep __version__ ./openmaptiles/__init__.py | sed -E 's/^(.*"([^"]+)".*|.*)$$/\2/')
IMAGE_NAME   ?= openmaptiles/openmaptiles-tools
DOCKER_IMAGE ?= $(IMAGE_NAME):$(VERSION)
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
	docker build --file Dockerfile $(foreach ver, $(VERSION), --tag $(IMAGE_NAME):$(ver)) .

.PHONY: build-all-dockers
build-all-dockers: build-docker
	# Docker-build all subdirectories in docker/*
	# For each dir, cd into it and do a docker build + tag with version
	# The build-arg OMT_TOOLS_VERSION is not needed by most of the builds, so it will show a warning
	@for dir in $$(find docker/* -maxdepth 0 -type d | sort) ; do \
	( \
		cd $$dir ; \
		echo "\n\n*****************************************************" ; \
		export IMG="openmaptiles/$${dir#docker/}" ; \
		echo "Building $(IMAGE_NAME) $(foreach ver, $(VERSION), tag $(ver)) in $$dir..." ; \
		if [ -n "$$DOCKER_PRUNE_ON_BUILD" ]; then \
			docker image prune --force ; \
		fi ; \
		if [ "$$dir" = "docker/postgis-preloaded" ]; then \
			docker build \
				--file Dockerfile \
				--build-arg OMT_TOOLS_VERSION=$(VERSION) \
				$(foreach ver, $(VERSION), --tag $$IMG:$(ver)) \
				. ; \
		else \
			docker build \
				--file Dockerfile \
				$(foreach ver, $(VERSION), --tag $$IMG:$(ver)) \
				. ; \
		fi ; \
	) ; \
	done

.PHONY: push-all-dockers
push-all-dockers: build-all-dockers
	@for image in $(foreach ver, $(VERSION), openmaptiles/openmaptiles-tools:$(ver)) ; do \
		echo "Uploading $$image" ; \
		docker push "$$image" ; \
	done
	@for dir in $$(find docker/* -maxdepth 0 -type d | sort) ; do \
		for image in $(foreach ver, $(VERSION), openmaptiles/$${dir#docker/}:$(ver)) ; do \
			echo "Uploading $$image" ; \
			docker push "$$image" ; \
		done ; \
	done


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
