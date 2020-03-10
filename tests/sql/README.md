This directory contains all the tests that require PostgreSQL database running as a second docker container.

* [docker-compose.yml](./docker-compose.yml) is used to start both the tester (tools image) and the PG server (postgis image)
* [test-sql.sh](./test-sql.sh) is ran on the tester
