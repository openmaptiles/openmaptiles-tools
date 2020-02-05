VERSION      ?= $(shell grep __version__ ./openmaptiles/__init__.py | sed -E 's/^(.*"([^"]+)".*|.*)$$/\2/')
IMAGE_NAME   ?= openmaptiles/openmaptiles-tools
DOCKER_IMAGE ?= $(IMAGE_NAME):$(VERSION)
BUILD_DIR    ?= build

# Options to run with docker - ensure the container is destroyed on exit,
# runs as the current user rather than root (so that created files are not root-owned)
DOCKER_OPTS  ?= -i --rm -u $$(id -u $${USER}):$$(id -g $${USER})

# Current dir is shared with the docker, allowing scripts to write to the dir as a current user
WORKDIR      ?= $$( pwd -P )
RUN_CMD := docker run ${DOCKER_OPTS} -v "$(WORKDIR):/tileset" "$(DOCKER_IMAGE)"

DIFF_CMD := diff --brief --recursive --new-file
EXPECTED_DIR := testdata/expected

# Exports
export DOCKER_IMAGE


.PHONY: test
test: clean build-tests
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Comparing built results with the expected ones"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(DIFF_CMD) "$(BUILD_DIR)" "$(EXPECTED_DIR)"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Python unit tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(RUN_CMD) python -m unittest
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
	docker build --pull --file Dockerfile --tag $(DOCKER_IMAGE) .

.PHONY: build-sql-tests
build-sql-tests: prepare build-docker
	# Run postgis (latest) image, import all SQL tools/languages code, and run the tests
	# Make sure to cleanup before and after to make sure no volume stays behind
	docker-compose --file test-sql/docker-compose.yml rm -f && \
	timeout 60 docker-compose --file test-sql/docker-compose.yml up --abort-on-container-exit && \
	docker-compose --file test-sql/docker-compose.yml rm -f

.PHONY: build-bin-tests
build-bin-tests: prepare build-docker
	$(RUN_CMD) sh -c 'export BUILD="/tileset/$(BUILD_DIR)" \
&& generate-tm2source testdata/testlayers/testmaptiles.yaml --host="pghost" --port=5432 --database="pgdb" --user="pguser" --password="pgpswd" > $$BUILD/tm2source.yml \
&& generate-imposm3  testdata/testlayers/testmaptiles.yaml                                      > $$BUILD/imposm3.yaml \
&& generate-sql      testdata/testlayers/testmaptiles.yaml                                      > $$BUILD/sql.sql \
&& generate-sql      testdata/testlayers/testmaptiles.yaml --dir $$BUILD/parallel_sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml                                      > $$BUILD/mvttile_func.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --key                                > $$BUILD/mvttile_func_key.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --psql                               > $$BUILD/mvttile_psql.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --prepared                           > $$BUILD/mvttile_prep.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query                              > $$BUILD/mvttile_query.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --gzip                       > $$BUILD/mvttile_query_gzip.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --gzip 9                     > $$BUILD/mvttile_query_gzip9.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --no-feature-ids             > $$BUILD/mvttile_query_no_feat_ids.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 2.4.0dev       > $$BUILD/mvttile_query_v2.4.0dev.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 2.5            > $$BUILD/mvttile_query_v2.5.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 3.0            > $$BUILD/mvttile_query_v3.0.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --test-geometry              > $$BUILD/mvttile_query_test_geom.sql \
&& generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --test-geometry --key        > $$BUILD/mvttile_query_test_geom_key.sql \
&& generate-doc      testdata/testlayers/housenumber/housenumber.yaml                           > $$BUILD/doc.md \
&& generate-sqlquery testdata/testlayers/housenumber/housenumber.yaml 14                        > $$BUILD/sqlquery.sql \
&& mkdir -p $$BUILD/devdoc \
&& generate-etlgraph testdata/testlayers/testmaptiles.yaml $$BUILD/devdoc --keep -f png -f svg \
&& generate-etlgraph testdata/testlayers/housenumber/housenumber.yaml $$BUILD/devdoc --keep -f png -f svg \
&& generate-mapping-graph testdata/testlayers/testmaptiles.yaml $$BUILD/devdoc --keep -f png -f svg \
&& generate-mapping-graph testdata/testlayers/housenumber/housenumber.yaml $$BUILD/devdoc/mapping_diagram --keep -f png -f svg \
&& download-osm planet --dry-run \
&& download-osm geofabrik michigan --dry-run \
'

.PHONY: build-tests
build-tests: build-bin-tests build-sql-tests
