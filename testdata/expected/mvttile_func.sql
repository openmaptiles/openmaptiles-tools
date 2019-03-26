CREATE OR REPLACE FUNCTION gettile(zoom integer, x integer, y integer)
RETURNS bytea AS $$
SELECT STRING_AGG(mvtl, '') AS mvt FROM (
  SELECT ST_AsMVT(tile, 'housenumber', 4096, 'mvtgeometry') as mvtl FROM (SELECT ST_AsMVTGeom(geometry, TileBBox(zoom, x, y), 4096, 8, true) AS mvtgeometry, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(TileBBox(zoom, x, y), zoom) WHERE ST_AsMVTGeom(geometry, TileBBox(zoom, x, y), 4096, 8, true) IS NOT NULL) AS tile HAVING COUNT(*) > 0
) AS all_layers
;
$$ LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT;
