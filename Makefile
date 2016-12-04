VERSION := $(shell cat VERSION)
DOCKER_IMAGE := openmaptiles/import-osm

.PHONY: release

release:
	@echo "Release: $(VERSION)"
	docker build -f Dockerfile      -t $(DOCKER_IMAGE):$(VERSION)      .
	docker images | grep $(DOCKER_IMAGE) | grep $(VERSION)
