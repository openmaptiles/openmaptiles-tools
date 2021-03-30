-- etldoc: layer_mountain_peak[shape=record fillcolor=lightpink,
-- etldoc:     style="rounded,filled", label="layer_mountain_peak | <z7_> z7+" ] ;

CREATE OR REPLACE FUNCTION layer_mountain_peak(bbox geometry,
                                               zoom_level integer,
                                               pixel_width numeric)
    RETURNS TABLE
            (
                osm_id   bigint,
                geometry geometry,
                name     text,
                name_en  text,
                name_de  text,
                class    text,
                tags     hstore,
                ele      int,
                ele_ft   int,
                "rank"   int
            )
AS
$$
SELECT
    -- etldoc: osm_peak_point -> layer_mountain_peak:z7_
    osm_id,
    geometry,
    name,
    name_en,
    name_de,
    tags->'natural' AS class,
    tags,
    ele::int,
    ele_ft::int,
    rank::int
FROM (
         SELECT osm_id,
                geometry,
                name,
                COALESCE(NULLIF(name_en, ''), name) AS name_en,
                COALESCE(NULLIF(name_de, ''), name, name_en) AS name_de,
                tags,
                substring(ele FROM E'^(-?\\d+)(\\D|$)')::int AS ele,
                round(substring(ele FROM E'^(-?\\d+)(\\D|$)')::int * 3.2808399)::int AS ele_ft,
                row_number() OVER (
                    PARTITION BY LabelGrid(geometry, 100 * pixel_width)
                    ORDER BY (
                            substring(ele FROM E'^(-?\\d+)(\\D|$)')::int +
                            (CASE WHEN NULLIF(wikipedia, '') IS NOT NULL THEN 10000 ELSE 0 END) +
                            (CASE WHEN NULLIF(name, '') IS NOT NULL THEN 10000 ELSE 0 END)
                        ) DESC
                    )::int AS "rank"
         FROM osm_peak_point
         WHERE geometry && bbox
           AND ele IS NOT NULL
           AND ele ~ E'^-?\\d{1,4}(\\D|$)'
     ) AS ranked_peaks
WHERE zoom_level >= 7
  AND (rank <= 5 OR zoom_level >= 14)
ORDER BY "rank" ASC;

$$ LANGUAGE SQL STABLE
                PARALLEL SAFE;
-- TODO: Check if the above can be made STRICT -- i.e. if pixel_width could be NULL
