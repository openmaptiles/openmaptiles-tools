-- Parse strings into numbers based on the 
-- postgis-vt-util CleanNumeric function
-- https://github.com/openmaptiles/postgis-vt-util/blob/master/src/CleanNumeric.sql
CREATE OR REPLACE FUNCTION omt_as_numeric(i text)
RETURNS NUMERIC AS
$$
SELECT COALESCE(CleanNumeric(i), -1);
$$
LANGUAGE SQL IMMUTABLE COST 50
PARALLEL SAFE;
