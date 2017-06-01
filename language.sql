CREATE OR REPLACE FUNCTION get_latin_name(tags hstore) RETURNS text AS $$
    SELECT COALESCE(
      NULLIF(tags->'name:en', ''),
      NULLIF(tags->'int_name', ''),
      CASE
        WHEN tags->'name' ~ '.*[a-zA-Z].*'
          THEN tags->'name'
        ELSE NULL
      END
    );
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION get_nonlatin_name(tags hstore) RETURNS text AS $$
    SELECT
      CASE
        WHEN tags->'name' !~ '.*[a-zA-Z].*'
          THEN tags->'name'
        ELSE NULL
      END;
$$ LANGUAGE SQL IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION get_name_int(tags hstore) RETURNS text AS $$
    SELECT
      COALESCE(
        NULLIF(tags->'int_name', ''),
        NULLIF(tags->'name:en', ''),
        tags->'name'
      );
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION get_basic_names(tags hstore) RETURNS hstore AS $$
DECLARE
  tags_array text[] := ARRAY[]::text[];
  name_latin text;
  name_nonlatin text;
  name_int text;
BEGIN
  name_latin := get_latin_name(tags);
  name_nonlatin := get_nonlatin_name(tags);
  name_int := get_name_int(tags);
  IF name_latin IS NOT NULL THEN
    tags_array := tags_array || ARRAY['name:latin', name_latin];
  END IF;
  IF name_nonlatin IS NOT NULL THEN
    tags_array := tags_array || ARRAY['name:nonlatin', name_nonlatin];
  END IF;
  IF name_int IS NOT NULL THEN
    tags_array := tags_array || ARRAY['name_int', name_int];
  END IF;
  RETURN hstore(tags_array);
END;
$$ STRICT
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION delete_empty_keys(tags hstore) RETURNS hstore AS $$
DECLARE
  result hstore;
BEGIN
  select
    hstore(array_agg(key), array_agg(value)) into result
  from
    each(hstore(tags))
  where nullif(value, '') is not null;
  RETURN result;
END;
$$ STRICT
LANGUAGE plpgsql IMMUTABLE;
