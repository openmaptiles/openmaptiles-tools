VERSION             ?= $(shell grep __version__ ./openmaptiles/__init__.py | sed -E 's/^(.*"([^"]+)".*|.*)$$/\2/')
IMAGE_NAME          ?= openmaptiles/openmaptiles-tools
export DOCKER_IMAGE ?= $(IMAGE_NAME):$(VERSION)

RUN_CMD := ./docker-run.sh
DIFF_CMD := diff --brief --recursive --new-file
EXPECTED_DIR := testdata/expected

.PHONY: test
test: clean build-tests
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Comparing built results with the expected ones"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(DIFF_CMD) build $(EXPECTED_DIR)
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	@echo "   Running Python unit tests"
	@echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	$(RUN_CMD) python -m unittest
	@echo "<<<<<<<<<<<<<<<<<<<<< SUCCESS <<<<<<<<<<<<<<<<<<<<<"

.PHONY: clean
clean:
	rm -rf build

# Ideally this list should be automated, but I haven't fonud a good way for Makefile to self-inspect for all build/* targets
# It might be possible to adapt https://stackoverflow.com/a/26339924/177275 , but will need to check if it works on Mac too
.PHONY: build-tests
build-tests: \
    build/tm2source.yml \
    build/imposm3.yaml \
    build/sql.sql \
    build/parallel_sql \
    build/mvttile_func.sql \
    build/mvttile_func_key.sql \
    build/mvttile_psql.sql \
    build/mvttile_prep.sql \
    build/mvttile_query.sql \
    build/mvttile_query_gzip.sql \
    build/mvttile_query_gzip9.sql \
    build/mvttile_query_no_feat_ids.sql \
    build/mvttile_query_v2.4.0dev.sql \
    build/mvttile_query_v2.5.sql \
    build/mvttile_query_v3.0.sql \
    build/mvttile_query_test_geom.sql \
    build/mvttile_query_test_geom_key.sql \
    build/doc.md \
    build/sqlquery.sql \
    build/devdoc

# Delete dir with the expected test results and rebuild them
.PHONY: rebuild-expected
rebuild-expected: clean build-tests
	rm -rf $(EXPECTED_DIR)
	mkdir -p $(EXPECTED_DIR)
	mv build/* $(EXPECTED_DIR)/

.PHONY: prepare
prepare: build-docker
	mkdir -p build

.PHONY: build-docker
build-docker:
	docker build --pull --file Dockerfile --tag $(DOCKER_IMAGE) .

#
# When adding a new target, make sure to also list it in the  "build-tests"  above
#

build/tm2source.yml: prepare
	$(RUN_CMD) generate-tm2source testdata/testlayers/testmaptiles.yaml --host="pghost" --port=5432 --database="pgdb" --user="pguser" --password="pgpswd" > $@
build/imposm3.yaml: prepare
	$(RUN_CMD) generate-imposm3  testdata/testlayers/testmaptiles.yaml                                      > $@
build/sql.sql: prepare
	$(RUN_CMD) generate-sql      testdata/testlayers/testmaptiles.yaml                                      > $@
build/parallel_sql: prepare
	$(RUN_CMD) generate-sql      testdata/testlayers/testmaptiles.yaml --dir $@
build/mvttile_func.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml                                      > $@
build/mvttile_func_key.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --key                                > $@
build/mvttile_psql.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --psql                               > $@
build/mvttile_prep.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --prepared                           > $@
build/mvttile_query.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query                              > $@
build/mvttile_query_gzip.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --gzip                       > $@
build/mvttile_query_gzip9.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --gzip 9                     > $@
build/mvttile_query_no_feat_ids.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --no-feature-ids             > $@
build/mvttile_query_v2.4.0dev.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 2.4.0dev       > $@
build/mvttile_query_v2.5.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 2.5            > $@
build/mvttile_query_v3.0.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --postgis-ver 3.0            > $@
build/mvttile_query_test_geom.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --test-geometry              > $@
build/mvttile_query_test_geom_key.sql: prepare
	$(RUN_CMD) generate-sqltomvt testdata/testlayers/testmaptiles.yaml --query --test-geometry --key        > $@
build/doc.md: prepare
	$(RUN_CMD) generate-doc      testdata/testlayers/housenumber/housenumber.yaml                           > $@
build/sqlquery.sql: prepare
	$(RUN_CMD) generate-sqlquery testdata/testlayers/housenumber/housenumber.yaml 14                        > $@
build/devdoc: prepare
	mkdir -p $@
	$(RUN_CMD) generate-etlgraph testdata/testlayers/housenumber/housenumber.yaml $@
