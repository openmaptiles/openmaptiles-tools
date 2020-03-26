DROP FUNCTION IF EXISTS gettile(integer, integer, integer);
CREATE FUNCTION gettile(zoom integer, x integer, y integer)
RETURNS bytea AS $$
SELECT STRING_AGG(mvtl, '') AS mvt FROM (
  SELECT COALESCE(ST_AsMVT(t, 'housenumber', 4096, 'mvtgeometry'), '') as mvtl, 0 as _layer_index FROM (SELECT ST_AsMVTGeom(geometry, ST_TileEnvelope(zoom, x, y), 4096, 8, true) AS mvtgeometry, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(ST_Expand(ST_TileEnvelope(zoom, x, y), 78271.51696402051/2^zoom), zoom)) AS t
    UNION ALL
  SELECT COALESCE(ST_AsMVT(t, 'enumfield', 4096, 'mvtgeometry', 'osm_id'), '') as mvtl, 1 as _layer_index FROM (SELECT osm_id, ST_AsMVTGeom(geometry, ST_TileEnvelope(zoom, x, y), 4096, 0, true) AS mvtgeometry, enumfield FROM layer_enumfields(ST_TileEnvelope(zoom, x, y), zoom)) AS t
    ORDER BY _layer_index
) AS all_layers
;
$$ LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT;
