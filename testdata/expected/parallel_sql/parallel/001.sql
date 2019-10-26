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
