VERSION := $(shell cat VERSION)
DOCKER_IMAGE      := openmaptiles/openmaptiles-tools
DOCKER_IMAGE_PY27 := openmaptiles/openmaptiles-tools_py27

.PHONY: test

test:
	mkdir -p ./testbuild/testmaptiles.tm2source
	mkdir -p ./testbuild/devdoc
	generate-tm2source testmaptiles.yaml --host="postgres" --port=5432 --database="testmaptiles" --user="testmaptiles" --password="testmaptiles" > ./testbuild/testmaptiles.tm2source/data.yml
	generate-imposm3 testmaptiles.yaml                              > ./testbuild/mapping.yaml
	generate-sql     testmaptiles.yaml                              > ./testbuild/tileset.sql
	generate-doc      ./testlayers/housenumber/housenumber.yaml     > ./testlayers/housenumber/README.md
	generate-sqlquery ./testlayers/housenumber/housenumber.yaml 14  > ./testbuild/sqlquery.sql
	generate-etlgraph ./testlayers/housenumber/housenumber.yaml ./testbuild/devdoc/
	md5sum -c checklist.chk

checklist:
	rm -f checklist.chk
	md5sum ./testbuild/testmaptiles.tm2source/data.yml  >> checklist.chk
	md5sum ./testbuild/mapping.yaml                     >> checklist.chk
	md5sum ./testbuild/tileset.sql                      >> checklist.chk
	md5sum ./testlayers/housenumber/README.md           >> checklist.chk
	md5sum ./testbuild/sqlquery.sql                     >> checklist.chk
	md5sum ./testbuild/devdoc/etl_housenumber.dot 		>> checklist.chk
	md5sum ./testbuild/devdoc/etl_housenumber.svg 		>> checklist.chk
	md5sum ./testbuild/devdoc/etl_housenumber.png 		>> checklist.chk
	cat checklist.chk

buildtest:
	@echo "Buildtest: $(VERSION)"
	docker build -f Dockerfile      -t $(DOCKER_IMAGE):$(VERSION)      .
	docker build -f Dockerfile.py27 -t $(DOCKER_IMAGE_PY27):$(VERSION) .
	docker images | grep  $(DOCKER_IMAGE) | grep $(VERSION)

release:
	@echo "Release: $(VERSION)"
	docker build -f Dockerfile      -t openmaptiles/openmaptiles-tools:$(VERSION)      .
	docker images | grep $(DOCKER_IMAGE) | grep -v $(DOCKER_IMAGE_PY27) | grep $(VERSION)
