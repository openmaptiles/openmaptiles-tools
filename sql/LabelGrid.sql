/******************************************************************************
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
******************************************************************************/
create or replace function LabelGrid (
        g geometry,
        grid_size numeric
    )
    returns text
    language plpgsql immutable
    parallel safe as
$func$
begin
    if grid_size <= 0 then
        return 'null';
    end if;
    if GeometryType(g) <> 'POINT' then
        g := (select (ST_DumpPoints(g)).geom limit 1);
    end if;
    return ST_AsText(ST_SnapToGrid(
        g,
        grid_size/2,  -- x origin
        grid_size/2,  -- y origin
        grid_size,    -- x size
        grid_size     -- y size
    ));
end;
$func$;


