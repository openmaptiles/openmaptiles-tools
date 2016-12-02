
build:
	docker build -t openmaptiles/import-osm .
	docker images | grep  openmaptiles/import-osm
