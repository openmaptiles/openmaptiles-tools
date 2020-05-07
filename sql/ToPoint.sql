/******************************************************************************
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
******************************************************************************/
create or replace function ToPoint (g geometry)
    returns geometry(point)
    language plpgsql immutable
    parallel safe as
$func$
begin
    g := ST_MakeValid(g);
    if GeometryType(g) = 'POINT' then
        return g;
    elsif ST_IsEmpty(g) then
        -- This should not be necessary with Geos >= 3.3.7, but we're getting
        -- mystery MultiPoint objects from ST_MakeValid (or somewhere) when
        -- empty objects are input.
        return null;
    elsif (GeometryType(g) = 'POLYGON' OR GeometryType(g) = 'MULTIPOLYGON') and ST_NPoints(g) <= 5 then
        -- For simple polygons the centroid is good enough for label placement
        return ST_Centroid(g);
    else
        return ST_PointOnSurface(g);
    end if;
end;
$func$;


