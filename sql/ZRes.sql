/******************************************************************************
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
******************************************************************************/
create or replace function ZRes (z integer)
    returns float
    returns null on null input
    language sql immutable
    parallel safe as
$func$
select (40075016.6855785/(256*2^z));
$func$;

create or replace function ZRes (z float)
    returns float
    returns null on null input
    language sql immutable
    parallel safe as
$func$
select (40075016.6855785/(256*2^z));
$func$;


