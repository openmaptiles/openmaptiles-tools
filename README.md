# OpenMapTiles Tools

The OpenMapTiles generation tools for generating TM2Source projects, imposm3 mappings and SQL instructions
from OpenMapTiles layers.

## Install

You need Python 2 or Python 3 installed on your system.

```
pip install openmaptiles-tools
# As long as we are not published to PyPI you can install directly from git
pip install git+https://github.com/openmaptiles/openmaptiles-tools
```

## Usage

### Generate TM2Source Projects for Mapbox Studio Classic

Takes a tileset definition an generates a TM2Source YAML project file.
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

### Generate ETL (Extract-Transform-Load ) graph 

Takes a source code from the imposm3 mapping file and the SQL postprocessing code , 
nad parsing for the `etldoc:` graphviz based comments, and generate an svg file.
The `.dot` and the `.svg` filename prefix is `etl_`

```
generate-etlgraph <tileset>
generate-etlgraph layers/landcover/landcover.yaml
generate-etlgraph layers/railway/railway.yaml
```

example:

input command: ` generate-etlgraph layers/landcover/landcover.yaml `
output fies:
- `layers/landcover/etl_landcover.dot`
- `layers/landcover/etl_landcover.svg`



###  Generate SQL query for a given layer and zoom level

example:
```
generate-sqlquery layers/landcover/landcover.yaml  14
```



