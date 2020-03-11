DO $$ BEGIN RAISE NOTICE 'Processing layer enumfield'; END$$;

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
