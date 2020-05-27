SELECT STRING_AGG(mvtl, '') AS mvt FROM (
  SELECT COALESCE(ST_AsMVT(t, 'housenumber', 4096, 'mvtgeometry'), '') as mvtl FROM (SELECT ST_Expand(TileBBox($1, $2, $3), 78271.51696402051/2^$1) as ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 8, true) AS mvtgeometry, $1 AS housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM (SELECT 'name:en=>"enname"'::hstore as tags) AS tt) AS t WHERE mvtgeometry IS NOT NULL
    UNION ALL
  SELECT COALESCE(ST_AsMVT(t, 'enumfield', 4096, 'mvtgeometry'), '') as mvtl FROM (SELECT TileBBox($1, $2, $3) as ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 0, true) AS mvtgeometry, $1 AS osm_id, 'foo' AS class) AS t WHERE mvtgeometry IS NOT NULL
) AS all_layers

