-- Delete prepared statement if it already exists
DO $$ BEGIN
IF EXISTS (SELECT * FROM pg_prepared_statements where name = 'gettile') THEN
  DEALLOCATE gettile;
END IF;
END $$;

-- Run this statement with   EXECUTE gettile(zoom, x, y)
PREPARE gettile(integer, integer, integer) AS
SELECT STRING_AGG(mvtl, '') AS mvt FROM (
SELECT IsEmpty, count(*) OVER () AS LayerCount, mvtl FROM (
  SELECT (sum(IsEmpty::int) != 0) AS IsEmpty, ST_AsMVT(mvtl2, 'housenumber', 4096, 'mvtgeometry') as mvtl FROM (SELECT CASE $1 <= 8 WHEN TRUE THEN FALSE ELSE ST_WITHIN(ST_GeomFromText('POLYGON((0 4096,0 0,4096 0,4096 4096,0 4096))', 3857), mvtgeometry) END AS IsEmpty, mvtgeometry, housenumber FROM (SELECT ST_AsMVTGeom(geometry, TileBBox($1, $2, $3), 4096, 8, true) AS mvtgeometry, housenumber FROM (SELECT geometry, housenumber, NULLIF(tags->'name:en', '') AS "name:en", NULLIF(tags->'name:de', '') AS "name:de", NULLIF(tags->'name:cs', '') AS "name:cs", NULLIF(tags->'name_int', '') AS "name_int", NULLIF(tags->'name:latin', '') AS "name:latin", NULLIF(tags->'name:nonlatin', '') AS "name:nonlatin" FROM layer_housenumber(TileBBox($1, $2, $3), $1)) AS t) AS mvtl1 WHERE mvtgeometry is not null) AS mvtl2 HAVING COUNT(*) > 0
) AS all_layers
) AS counter_layers
HAVING BOOL_AND(NOT IsEmpty OR LayerCount <> 1);
