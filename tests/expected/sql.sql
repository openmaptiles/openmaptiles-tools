-- This SQL code should be executed first

CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY['name:en', 'name:de', 'name:cs', 'int_name', 'loc_name', 'name', 'wikidata', 'wikipedia']))
$$ LANGUAGE SQL IMMUTABLE;

DO $$ BEGIN RAISE NOTICE 'Processing layer housenumber'; END$$;

-- Layer housenumber - ./housenumber_centroid.sql


-- etldoc: osm_housenumber_point -> osm_housenumber_point
UPDATE osm_housenumber_point SET geometry=topoint(geometry)
WHERE ST_GeometryType(geometry) <> 'ST_Point';

-- Layer housenumber - ./layer.sql


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
) /* DELAY_MATERIALIZED_VIEW_CREATION */ ;

DO $$ BEGIN RAISE NOTICE 'Finished layer housenumber'; END$$;

DO $$ BEGIN RAISE NOTICE 'Processing layer enumfield'; END$$;

-- Layer enumfield - ./enumfield.sql

CREATE OR REPLACE FUNCTION map_landuse_class("natural" VARCHAR, landuse VARCHAR) RETURNS TEXT AS $$
    SELECT CASE
        WHEN "natural" = 'bare_rock' THEN 'rock'
        WHEN "natural" = 'grassland'
            OR "landuse" IN ('grass', 'allotments', 'grassland', 'park', 'village_green', 'recreation_ground')
            OR "landuse" LIKE 'meadow%'
            THEN 'grass'
        WHEN "subclass" IN ('school', 'kindergarten')
            OR "subclass" LIKE 'uni%'
            THEN 'school'
        WHEN ("subclass" = 'station' AND "mapping_key" = 'railway')
            OR "subclass" IN ('halt', 'tram_stop', 'subway')
            THEN 'railway'
        WHEN "field1" = 'a1fld1'
            AND ("field2" IN ('a1fld2a', 'a1fld2c') OR "field2" LIKE '%a1fld2b%')
            AND "field3" = 'a1fld3'
            THEN 'andfield'
        WHEN "fld1" = 'lf1'
            OR ("fld2" IN ('lf2a', 'lf2b') OR "fld3" = 'lf3')
            OR ("fld4" = 'lf4' OR "fld5" IN ('lf5a', 'lf5b') OR "fld5" LIKE 'lf5c%')
            OR ("fld6" = 'lf6' AND ("fld7" IN ('lf7a', 'lf7b') OR "fld7" LIKE 'lf7c%'))
            OR ("fld8" = 'lf8' AND ("fld9" IN ('lf9a', 'lf9b') OR "fld10" = 'lf10') AND ("fld11" = 'lf11' OR "fld12" IN ('lf12a', 'lf12b') OR "fld12" LIKE 'lf12c%'))
            THEN 'listfield'
END;
$$ LANGUAGE SQL IMMUTABLE;

DO $$ BEGIN RAISE NOTICE 'Finished layer enumfield'; END$$;

DO $$ BEGIN RAISE NOTICE 'Processing layer mountain_peak'; END$$;

DO $$ BEGIN
    PERFORM 'my_magic_table'::regclass;
EXCEPTION
    WHEN undefined_table THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'this table or view is required for layer "mountain_peak"';
END;
$$ LANGUAGE 'plpgsql';

DO $$ BEGIN
    PERFORM 'my_magic_func(TEXT, TEXT)'::regprocedure;
EXCEPTION
    WHEN undefined_function THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'this function is required for layer "mountain_peak"';
    WHEN invalid_text_representation THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'Required function "my_magic_func(TEXT, TEXT)" in layer "mountain_peak" is incorrectly declared. Use full function signature with parameter types, e.g. "my_magic_func(TEXT, TEXT)"';
END;
$$ LANGUAGE 'plpgsql';

DO $$ BEGIN RAISE NOTICE 'Finished layer mountain_peak'; END$$;

-- This SQL code should be executed last

