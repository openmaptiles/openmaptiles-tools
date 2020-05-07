# SQL Utilities

A set of tile-related PostgreSQL functions, some of which were adapted from the [mapbox/postgis-vt-util](https://github.com/mapbox/postgis-vt-util) project.
To rebuild this documentation, run `make README.md`.

The files will be imported in alphabeticall order.

## Function Reference

<!-- DO NOT EDIT BELOW THIS LINE - AUTO-GENERATED FROM SQL COMMENTS by  make README.md  -->


### CleanNumeric ###

Returns the input text as an numeric if possible, otherwise null.

__Parameters:__

- `text` i - Text that you would like as an numeric.

__Returns:__ `numeric`


### LabelGrid ###

Returns a "hash" of a geometry's position on a specified grid to use in a GROUP
BY clause. Useful for limiting the density of points or calculating a localized
importance ranking.

This function is most useful on point geometries intended for label placement
(eg points of interest) but will accept any geometry type. It is usually used
as part of either a `DISTINCT ON` expression or a `rank()` window function.

__Parameters:__

- `geometry` g - A geometry.
- `numeric` grid_size - The cell size of the desired grouping grid.

__Returns:__ `text` - A text representation of the labelgrid cell

__Example Mapbox Studio query:__

```sql
(   SELECT * FROM (
        SELECT DISTINCT ON (LabelGrid(geom, 64*!pixel_width!)) * FROM (
            SELECT id, name, class, population, geom FROM city_points
            WHERE geom && !bbox!
        ) AS raw
        ORDER BY LabelGrid(geom, 64*!pixel_width!), population DESC, id
    ) AS filtered
    ORDER BY population DESC, id
) AS final
```


### LineLabel ###

This function tries to estimate whether a line geometry would be long enough to
have the given text placed along it at the specified scale.

It is useful in vector tile queries to filter short lines from zoom levels
where they would be unlikely to have text places on them anyway.

__Parameters:__

- `numeric` zoom - The Web Mercator zoom level you are considering.
- `text` label - The label text that you will be placing along the line.
- `geometry(linestring)` g - A line geometry.

__Returns:__ `boolean`


### TileBBox ###

Given a Web Mercator tile ID as (z, x, y), returns a bounding-box
geometry of the area covered by that tile.

__Parameters:__

- `integer` z - A tile zoom level.
- `integer` x - A tile x-position.
- `integer` y - A tile y-position.
- `integer` srid - SRID of the desired target projection of the bounding
  box. Defaults to 3857 (Web Mercator).

__Returns:__ `geometry(polygon)`


### ToPoint ###

Helper to wrap ST_PointOnSurface, ST_MakeValid. This is needed because
of a ST_PointOnSurface bug in geos < 3.3.8 where POLYGON EMPTY can pass
through as a polygon geometry.
If the input geometry is a polygon with less than 5 points the ST_Centroid
of the polygon will be used instead of ST_PointOnSurface to speed up calculation.

__Parameters:__

- `geometry` g - A geometry.

__Returns:__ `geometry(point)`

__Example:__

```sql
-- Create an additional point geometry colums for labeling
ALTER TABLE city_park ADD COLUMN geom_label geometry(point);
UPDATE city_park SET geom_label = ToPoint(geom);
```


### ZRES ###

Takes a web mercator zoom level and returns the pixel resolution for that
scale, assuming 256x256 pixel tiles. Non-integer zoom levels are accepted.

__Parameters:__

- `integer` or `float` z - A Web Mercator zoom level.

__Returns:__ `float`

__Examples:__

```sql
-- Delete all polygons smaller than 1px square at zoom level 10
DELETE FROM water_polygons WHERE sqrt(ST_Area(geom)) < ZRes(10);

-- Simplify geometries to a resolution appropriate for zoom level 10
UPDATE water_polygons SET geom = ST_Simplify(geom, ZRes(10));
```


### Z ###

Returns a Web Mercator integer zoom level given a scale denominator.

Useful with Mapnik's !scale_denominator! token in vector tile source
queries.

__Parameters:__

- `numeric` scale_denominator - The denominator of the scale, eg `250000`
  for a 1:250,000 scale.

__Returns:__ `integer`

__Example Mapbox Studio query:__

```sql
( SELECT * FROM roads
  WHERE Z(!scale_denominator!) >= 12
) AS data
```

