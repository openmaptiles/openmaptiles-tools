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


CREATE OR REPLACE FUNCTION remove_latin(text) RETURNS text AS $$
  DECLARE
    i integer;
  DECLARE
    letter text;
    result text = '';
  BEGIN
    FOR i IN 1..char_length($1) LOOP
      letter := substr($1, i, 1);
      IF (unaccent(letter) !~ '^[a-zA-Z].*') THEN
        result := result || letter;
      END IF;
    END LOOP;
    result := regexp_replace(result, '(\([ -.]*\)|\[[ -.]*\])', '');
    result := regexp_replace(result, ' +\. *$', '');
    result := trim(both ' -\n' from result);
    RETURN result;
  END;
$$ LANGUAGE 'plpgsql' IMMUTABLE;


CREATE OR REPLACE FUNCTION get_latin_name(tags hstore, geometry geometry) RETURNS text AS $$
    SELECT COALESCE(
      CASE
        WHEN tags->'name' is not null and osml10n_is_latin(tags->'name')
          THEN tags->'name'
        ELSE NULL
      END,
      NULLIF(tags->'name:en', ''),
      NULLIF(tags->'int_name', ''),
      NULLIF(osml10n_get_name_without_brackets_from_tags(tags, 'en', geometry), '')
    );
$$ LANGUAGE SQL IMMUTABLE STRICT;


CREATE OR REPLACE FUNCTION get_nonlatin_name(tags hstore) RETURNS text AS $$
    SELECT
      CASE
        WHEN tags->'name' is not null and osml10n_is_latin(tags->'name')
          THEN NULL
        WHEN unaccent(tags->'name') ~ '[a-zA-Z]'
          THEN remove_latin(tags->'name')
        ELSE tags->'name'
      END;
$$ LANGUAGE SQL IMMUTABLE STRICT;

CREATE OR REPLACE FUNCTION get_basic_names(tags hstore, geometry geometry) RETURNS hstore AS $$
DECLARE
  tags_array text[] := ARRAY[]::text[];
  name_latin text;
  name_nonlatin text;
  name_int text;
BEGIN
  name_latin := get_latin_name(tags, geometry);
  name_nonlatin := get_nonlatin_name(tags);
  IF (name_nonlatin = name_latin) THEN
    name_nonlatin := null;
  END IF;
  name_int := COALESCE(
    NULLIF(tags->'int_name', ''),
    NULLIF(tags->'name:en', ''),
    NULLIF(name_latin, ''),
    tags->'name'
  );
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


CREATE OR REPLACE FUNCTION merge_wiki_names(tags hstore) RETURNS hstore AS $$
DECLARE
  result hstore;
BEGIN

  IF (tags ? 'wikidata' OR tags ? 'wikipedia') THEN
    select INTO result
    CASE
      WHEN avals(wd.labels) && avals(tags)
        THEN slice_language_tags(wd.labels) || tags
      ELSE tags
    END
    FROM wd_names wd
    WHERE wd.id = tags->'wikidata' OR wd.page = tags->'wikipedia';
    IF result IS NULL THEN
      result := tags;
    END IF;
  ELSE
    result := tags;
  END IF;

  RETURN result;
END;
$$ STRICT
LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION update_tags(tags hstore, geometry
  geometry) RETURNS hstore AS $$
DECLARE
  result hstore;
BEGIN
  result := delete_empty_keys(tags) || get_basic_names(tags, geometry);
  result := merge_wiki_names(result);
  RETURN result;
END;
$$ STRICT
LANGUAGE plpgsql IMMUTABLE;
