# OpenMapTiles Tools [![Build Status](https://api.travis-ci.org/openmaptiles/openmaptiles-tools.svg?branch=master)](https://travis-ci.org/openmaptiles/openmaptiles-tools) [![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/openmaptiles-tools.svg)](https://hub.docker.com/r/openmaptiles/openmaptiles-tools) [![](https://images.microbadger.com/badges/image/openmaptiles/openmaptiles-tools.svg)](https://microbadger.com/images/openmaptiles/openmaptiles-tools)

The OpenMapTiles tools for generating TM2Source projects, imposm3 mappings and SQL instructions
from OpenMapTiles layers. We encourage other people to use this for their vector tile projects as well since this approach works well for us.

Check out the [OpenMapTiles project](https://github.com/openmaptiles/openmaptiles/) for a real world example.

## Usage

You need either just Docker or Python 3 installed on your system.  If running without Docker, some of the scripts require `graphviz` and `sqlite3` dependencies.

#### Usage with Docker

The easiest is to use docker directly to run this command. You do not need to clone `openmaptiles-tools` locally, just clone the [openmaptiles repo](https://github.com/openmaptiles/openmaptiles) and run from its root.

_**Note:** container scripts can only access files from the given directory and below, e.g. in this example - `${PWD}` - current dir._
```bash
docker run -it --rm -u $(id -u ${USER}):$(id -g ${USER}) \
           -v "${PWD}:/tileset" \
           openmaptiles/openmaptiles-tools \
           <script-name> <script-parameters>
```

Where the `<script-name>` could be any of the scripts in the [bin/](./bin) directory, e.g. `generate-imposm3 openmaptiles.yaml`.

#### Using without Docker

```bash
python3 -m pip install openmaptiles-tools
# OR you can also install the package directly from git
python3 -m pip install git+https://github.com/openmaptiles/openmaptiles-tools

# Some tool require these packages. On Debian/Ubuntu you can install them with
sudo apt install graphviz sqlite3

# Run the script you want, e.g. from the openmaptiles dir:
generate-imposm3 openmaptiles.yaml

# If the script doesn't run, make sure your PATH includes default PIP bin directory.
# On Debian/Ubuntu that would be  ~/.local/bin/  (under your home dir).
# Otherwise just run it with  ~/.local/bin/generate-imposm3 ...
```

#### Running from source

Make sure you have all dependencies from the [Usage](#Usage) section above.
```bash
# Get OpenMapTiles layer data
git clone https://github.com/openmaptiles/openmaptiles.git
# Get the tools repo
git clone https://github.com/openmaptiles/openmaptiles-tools.git
# Run scripts from the root of the tools repository
cd openmaptiles-tools
# The PYTHONPATH=$PWD allows script to find its modules located in the current dir.
PYTHONPATH=$PWD python3 bin/generate-imposm3 ../openmaptiles/openmaptiles.yaml
```

#### Development

Use `make test` to run all of the tests locally.  The Makefile will build a docker image with all the code, run all tests, and compare the build result with the files in the [testdata/expected](./testdata/expected) dir.

Run `make rebuild-expected` after you modify the output produced by the generation scripts. This will re-create the expected test results to match the actual ones, and make sure the changes are what you want. 

## Data Concepts

You define a self contained **Layer** together with SQL files and layer and data source definitions (like an imposm3 mapping file) that you can then reference in a **Tileset** where you mix and match with other layers.


### Define your own Layer

Take a look or copy a standard layer like [building](https://github.com/openmaptiles/openmaptiles/tree/master/layers/building) to get started with your own layer.
A layer consists out of a **Layer** definition written in YAML format.

There you specify the `layer` properties like `id`, `buffer_size` and possible Markdown documentation (`description` and `fields`).
You can also reference SQL files in `schema` for writing the necessary queries for your layer or create generalized tables.
We encourage you to have a function per layer which takes the bounding box and zoom level. This makes it easy
to test and reuse.

If your data is based of OSM you can also directly
reference a [imposm3 mapping file](https://imposm.org/docs/imposm3/latest/mapping.html) to choose the OSM data you need.

```yaml
layer:
  id: "building"
  description: Buildings from OpenStreetMap
  buffer_size: 4
  datasource:
    query: (SELECT geometry FROM layer_building(!bbox!, z(!scale_denominator!))) AS t
  fields:
    render_height: An approximated height from levels and height of building.
schema:
  - ./building.sql
datasources:
  - type: imposm3
    mapping_file: ./mapping.yaml
```

### Define your own Tileset

A **Tileset** defines which layer will be in your vector tile set (`layers`)
and metadata used for generating a TM2Source project to actually generate the vector tiles.

```yaml
tileset:
  layers:
    - layers/building/building.yaml
    - layers/housenumber/housenumber.yaml
    - layers/poi/poi.yaml
  name: Street Level
  description: A tileset showing street level info like building, housenumbers and POIs.
  attribution: "OpenStreetMap contributors"
  maxzoom: 14
  minzoom: 13
  center: [-12.2168, 28.6135, 4]
  bounds: [-180.0,-85.0511,180.0,85.0511]
```

## Scripts

### Generate SQL code to create MVT tiles directly by PostGIS

Uses tileset definition to create a PostgreSQL
 [prepared](https://www.postgresql.org/docs/current/sql-prepare.html) or
 [create function](https://www.postgresql.org/docs/9.1/sql-createfunction.html) SQL code
 to generate an entire vector tile in the Mapbox Vector Tile format with a single `getTile(z,x,y)` query
 using PostGIS MVT support.
 
Use `--help` to get all parameters.

**NOTE:** Current [openmaptiles/postgis](https://github.com/openmaptiles/postgis) image (v2.9 and before) has incorrect support for the [ST_AsMVT()](https://postgis.net/docs/ST_AsMVT.html). Until Postgis is updated, please use [sophox/postgis docker image](https://hub.docker.com/r/sophox/postgis) (based on the latest [mdillon/postgis:11](https://hub.docker.com/r/mdillon/postgis) base image).

```
generate-sqltomvt <tileset>
```

### Generate Imposm3 Mapping File

Takes a tileset definition an generates an imposm3 mapping file for importing OSM data.

```
generate-imposm3 <tileset>
```

### Collect SQL schemas

Takes a tileset definition and collects all SQL referenced in the layer definitions.

```
generate-sql <tileset>
```

### Generate Markdown Documentation

Takes a tileset definition and generates Markdown documentation.

```
generate-doc <tileset>
```

### Generate ETL (Extract-Transform-Load) graph

dependency:  graphviz

Takes a source code from the imposm3 mapping file and the SQL postprocessing code,
and parsing for the `etldoc:` graphviz based comments, and generate an svg file.
The `.dot` and the `.svg` filename prefix is `etl_`

```
generate-etlgraph <tileset>  <target-directory>
generate-etlgraph layers/landcover/landcover.yaml  ./build/devdoc
generate-etlgraph layers/railway/railway.yaml      ./build/etlgraph
```

example:

input command: `generate-etlgraph layers/landcover/landcover.yaml`
output fies:
- `layers/landcover/etl_landcover.dot`
- `layers/landcover/etl_landcover.svg`


###  Generate SQL query for a given layer and zoom level

example:
```
generate-sqlquery layers/landcover/landcover.yaml  14
```

### Add simple metadata to mbtiles file

dependency:  sqlite3

example:
```
generate_metadata ./data/tiles.mbtiles
```

### Generate TM2Source Projects for Mapbox Studio Classic

Takes a tileset definition and generates a TM2Source YAML project file.
You need to provide PostgreSQL database connection settings before generating the project.

```
generate-tm2source <tileset> --host="localhost" --port=5432 --database="osm" --user="osm" --password="osm"
```

# Test tiles

Postserve is an OpenMapTiles map vector tile test server that dynamically generates metadata and tiles
 directly from PostgreSQL database based on the tileset file definition. Use `--help` for all parameters.

```
postserve <tileset> ...
```

Use `postserve <tileset>` to start serving. Use `--help` to get the list of Postgres connection parameters.

## Postserve quickstart with docker
* clone [openmaptiles repo](https://github.com/openmaptiles/openmaptiles) (`openmaptiles-tools` repo is not needed with docker)
* get a PostgreSQL server running with the openmaptiles-imported OSM data, e.g. by following quickstart guide.
* run `docker pull openmaptiles/openmaptiles-tools` to download the latest tools version
* from inside the openmaptiles repo dir, run this command.
(This assumes PostgreSQL is on the localhost:5432, but if it runs inside docker, you may want to change `--net=host` to `--net=openmaptiles_postgres_conn` to match the openmaptiles quickstart, and also expose port 8090 to the host with `-p 8090:8090`)
```
docker run -it --rm -u $(id -u ${USER}):$(id -g ${USER}) \
    -v "${PWD}:/tileset" --net=host \
    openmaptiles/openmaptiles-tools \
    postserve openmaptiles.yaml 
```

Add `--help` to see all additional parameters.

* Run Maputnik and set its data source to `http://localhost:8090`
