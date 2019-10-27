SELECT STRING_AGG(mvtl, '') AS mvt FROM (
SELECT IsEmpty, count(*) OVER () AS LayerCount, mvtl FROM (
  SELECT FALSE AS IsEmpty, ST_AsMVT(tile, 'housenumber', 4096, 'mvtgeometry') as mvtl FROM (SELECT ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 8, true) AS mvtgeometry, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(TileBBox($1, $2, $3), $1) WHERE ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 8, true) IS NOT NULL) AS tile HAVING COUNT(*) > 0
) AS all_layers
) AS counter_layers
HAVING BOOL_AND(NOT IsEmpty OR LayerCount <> 1)
