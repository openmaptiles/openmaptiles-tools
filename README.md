# OpenMapTiles Tools [![Build Status](https://api.travis-ci.org/openmaptiles/openmaptiles-tools.svg?branch=master)](https://travis-ci.org/openmaptiles/openmaptiles-tools) [![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/openmaptiles-tools.svg)](https://hub.docker.com/r/openmaptiles/openmaptiles-tools) [![](https://images.microbadger.com/badges/image/openmaptiles/openmaptiles-tools.svg)](https://microbadger.com/images/openmaptiles/openmaptiles-tools)

The OpenMapTiles tools for generating TM2Source projects, imposm3 mappings and SQL instructions
from OpenMapTiles layers. We encourage other people to use this for their vector tile projects as well since this approach works well for us.

Check out the [OpenMapTiles project](https://github.com/openmaptiles/openmaptiles/) for a real world example.

## Install

You need Python 2 or Python 3 installed on your system.
External dependency:  graphviz, sqlite3

```bash
pip install openmaptiles-tools
# You can also install the package directly from git
pip install git+https://github.com/openmaptiles/openmaptiles-tools

# Some tool call external command,  you can install them on debian / ubuntu :
apt-get install  graphviz sqlite3

```

## Concepts

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

## Usage

### Generate TM2Source Projects for Mapbox Studio Classic

Takes a tileset definition and generates a TM2Source YAML project file.
You need to provide PostgreSQL database connection settings before generating the project.

```
generate-tm2source <tileset> --host="localhost" --port=5432 --database="osm" --user="osm" --password="osm"
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
