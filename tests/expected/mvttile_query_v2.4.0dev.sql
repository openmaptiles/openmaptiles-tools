SELECT STRING_AGG(mvtl, '') AS mvt FROM (
  SELECT COALESCE(ST_AsMVT('housenumber', 4096, 'mvtgeometry', t), '') as mvtl FROM (SELECT ST_Expand(TileBBox($1, $2, $3), 1252344.2714243282/2^$1) as ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 128, true) AS mvtgeometry, $1 AS housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM (SELECT 'name:en=>"enname"'::hstore as tags) AS tt) AS t WHERE mvtgeometry IS NOT NULL
    UNION ALL
  SELECT COALESCE(ST_AsMVT('enumfield', 4096, 'mvtgeometry', t), '') as mvtl FROM (SELECT TileBBox($1, $2, $3) as ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 0, true) AS mvtgeometry, $1 AS osm_id, 'foo' AS class) AS t WHERE mvtgeometry IS NOT NULL
    UNION ALL
  SELECT COALESCE(ST_AsMVT('mountain_peak', 4096, 'mvtgeometry', t), '') as mvtl FROM (SELECT ST_Expand(TileBBox($1, $2, $3), 10018754.171394626/2^$1) AS ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 1024, true) AS mvtgeometry, $1 AS osm_id, 'foo_name' AS name, 'foo_name_en' AS name_en, 'foo_name_de' AS name_de, 'foo_class' AS class, $1 AS ele, $1 AS ele_ft, $1 AS rank) AS t WHERE mvtgeometry IS NOT NULL
) AS all_layers

