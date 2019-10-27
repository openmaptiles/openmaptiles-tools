CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY['name:en', 'name:de', 'name:cs', 'int_name', 'loc_name', 'name', 'wikidata', 'wikipedia']))
$$ LANGUAGE SQL IMMUTABLE;
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

DO $$ BEGIN RAISE NOTICE 'Finished layer housenumber'; END$$;

DO $$ BEGIN RAISE NOTICE 'Processing layer enumfield'; END$$;

CREATE OR REPLACE FUNCTION map_landuse_class("natural" VARCHAR, landuse VARCHAR) RETURNS TEXT AS $$
    SELECT CASE
        WHEN "natural"='bare_rock' THEN 'rock'
        WHEN "natural"='grassland'
            OR "landuse" IN ('grass', 'allotments', 'grassland', 'park', 'village_green', 'recreation_ground')
            OR "landuse" LIKE 'meadow%'
            THEN 'grass'
        ELSE NULL
END;
$$ LANGUAGE SQL IMMUTABLE;

DO $$ BEGIN RAISE NOTICE 'Finished layer enumfield'; END$$;

