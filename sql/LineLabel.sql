/******************************************************************************
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
******************************************************************************/
create or replace function LineLabel (
        zoom numeric,
        label text,
        g geometry
    )
    returns boolean
    language plpgsql immutable
    parallel safe as
$func$
begin
    if zoom > 20 or ST_Length(g) = 0 then
        -- if length is 0 geom is (probably) a point; keep it
        return true;
    else
        return length(label) between 1 and ST_Length(g)/(2^(20-zoom));
    end if;
end;
$func$;


