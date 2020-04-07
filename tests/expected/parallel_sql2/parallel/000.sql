DO $$ BEGIN RAISE NOTICE 'Processing layer housenumber'; END$$;

-- etldoc: osm_housenumber_point -> osm_housenumber_point
UPDATE osm_housenumber_point SET geometry=topoint(geometry)
WHERE ST_GeometryType(geometry) <> 'ST_Point';

-- etldoc: layer_housenumber[shape=record fillcolor=lightpink, style="rounded,filled",
-- etldoc:     label="layer_housenumber | <z14_> z14_" ] ;

CREATE OR REPLACE FUNCTION layer_housenumber(bbox geometry, zoom_level integer)
RETURNS TABLE(osm_id bigint, geometry geometry, housenumber text, tags hstore) AS $$
   -- etldoc: osm_housenumber_point -> layer_housenumber:z14_
    SELECT osm_id, geometry, housenumber, tags FROM osm_housenumber_point
    WHERE zoom_level >= 14 AND geometry && bbox;
$$ LANGUAGE SQL IMMUTABLE;


DROP MATERIALIZED VIEW IF EXISTS layer_housenumber_gen1 CASCADE;
CREATE MATERIALIZED VIEW layer_housenumber_gen1 AS (
  SELECT ST_Simplify(geometry, 10) AS geometry, osm_id, housenumber
  FROM osm_housenumber_point
)  WITH NO DATA  ;

DO $$ BEGIN RAISE NOTICE 'Finished layer housenumber'; END$$;
