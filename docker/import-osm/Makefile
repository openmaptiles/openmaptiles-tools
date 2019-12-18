VERSION ?= $(shell grep __version__ ../../openmaptiles/__init__.py | sed -E 's/^(.*"([^"]+)".*|.*)$$/\2/')
DOCKER_IMAGE ?= openmaptiles/import-osm

.PHONY: build
build:
	@echo "Build: $(VERSION)"
	docker build -f Dockerfile -t $(DOCKER_IMAGE):$(VERSION) .
	docker images | grep $(DOCKER_IMAGE) | grep $(VERSION)

.PHONY: release
release:
	@echo "Release: $(VERSION)"
	docker build --pull -f Dockerfile -t $(DOCKER_IMAGE):$(VERSION) .
	docker images | grep $(DOCKER_IMAGE) | grep $(VERSION)

# Build with custom legacy imposm version
.PHONY: release-legacy
release-legacy:
	docker build \
		--build-arg IMPOSM_REPO="https://github.com/openmaptiles/imposm3.git" \
		--build-arg IMPOSM_VERSION="v2017-10-18" \
		--pull -f Dockerfile -t $(DOCKER_IMAGE):$(VERSION)-legacy .
	docker images | grep $(DOCKER_IMAGE) | grep $(VERSION)-legacy

# Build latest stable imposm version
.PHONY: release-latest
release-latest:
	docker build \
		--build-arg IMPOSM_REPO="https://github.com/omniscale/imposm3.git" \
		--build-arg IMPOSM_VERSION="v0.8.1" \
		--pull -f Dockerfile -t $(DOCKER_IMAGE):$(VERSION)-stable .
	docker images | grep $(DOCKER_IMAGE) | grep $(VERSION)-stable
