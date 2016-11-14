
.PHONY: test

test:
	mkdir -p build/testmaptiles.tm2source && generate-tm2source testmaptiles.yaml --host="postgres" --port=5432 --database="testmaptiles" --user="testmaptiles" --password="testmaptiles" > build/testmaptiles.tm2source/data.yml
	mkdir -p build && generate-imposm3 testmaptiles.yaml      > build/mapping.yaml
	mkdir -p build && generate-sql     testmaptiles.yaml      > build/tileset.sql
	generate-doc      testlayers/housenumber/housenumber.yaml > testlayers/housenumber/README.md
	generate-etlgraph testlayers/housenumber/housenumber.yaml
	ls  testlayers/housenumber/* -la
	ls  build/* -la

buildtest:
	docker build -f Dockerfile      -t openmaptiles/openmaptiles-tools      .
	docker build -f Dockerfile.py27 -t openmaptiles/openmaptiles-tools_py27 .
