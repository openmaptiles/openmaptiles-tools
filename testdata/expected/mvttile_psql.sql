SELECT STRING_AGG(mvtl, '') AS mvt FROM (
  SELECT COALESCE(ST_AsMVT(t, 'housenumber', 4096, 'mvtgeometry'), '') as mvtl FROM (SELECT ST_AsMVTGeom(geometry, TileBBox(:zoom, :x, :y), 4096, 8, true) AS mvtgeometry, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(TileBBox(:zoom, :x, :y), :zoom)) AS t
    UNION ALL
  SELECT COALESCE(ST_AsMVT(t, 'enumfield', 4096, 'mvtgeometry'), '') as mvtl FROM (SELECT ST_AsMVTGeom(geometry, TileBBox(:zoom, :x, :y), 4096, 0, true) AS mvtgeometry, enumfield FROM layer_enumfields(TileBBox(:zoom, :x, :y), :zoom)) AS t
) AS all_layers

