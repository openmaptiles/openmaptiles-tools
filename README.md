# OpenMapTiles Tools

The OpenMapTiles generation tools for generating TM2Source projects, imposm3 mappings and SQL instructions
from OpenMapTiles layers.

## Install

Install the Python package.

```
pip install openmaptiles-tools
```

## Tools

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
