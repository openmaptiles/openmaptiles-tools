SELECT STRING_AGG(mvtl, '') AS mvt, SUM(COALESCE(bad_geos, 0)) as bad_geos FROM (
  SELECT COALESCE(ST_AsMVT(t, 'housenumber', 4096, 'mvtgeometry'), '') as mvtl, SUM((1-COALESCE(ST_IsValid(mvtgeometry)::int, 1))+COALESCE(bad_geos, 0)) as bad_geos, 0 as _layer_index FROM (SELECT ST_AsMVTGeom(geometry, ST_TileEnvelope($1, $2, $3), 4096, 8, true) AS mvtgeometry, (1-ST_IsValid(geometry)::int) as bad_geos, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(ST_Expand(ST_TileEnvelope($1, $2, $3), 78271.51696402051/2^$1), $1)) AS t
    UNION ALL
  SELECT COALESCE(ST_AsMVT(t, 'enumfield', 4096, 'mvtgeometry', 'osm_id'), '') as mvtl, SUM((1-COALESCE(ST_IsValid(mvtgeometry)::int, 1))+COALESCE(bad_geos, 0)) as bad_geos, 1 as _layer_index FROM (SELECT osm_id, ST_AsMVTGeom(geometry, ST_TileEnvelope($1, $2, $3), 4096, 0, true) AS mvtgeometry, (1-ST_IsValid(geometry)::int) as bad_geos, enumfield FROM layer_enumfields(ST_TileEnvelope($1, $2, $3), $1)) AS t
    ORDER BY _layer_index
) AS all_layers

