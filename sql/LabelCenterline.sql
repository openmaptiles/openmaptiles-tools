/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates a linestring suitable for a label.

__Parameters:__

- `geometry` input - A polygon or multipolygon.

__Returns:__ `geometry(linestring)`
******************************************************************************/
CREATE OR REPLACE FUNCTION CountDisconnectedEndpoints(polyline geometry, line geometry) RETURNS integer
    AS 'SELECT ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(polyline)))
                    - ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(ST_Difference(polyline, line))))
                    - ST_NPoints(line) + 2;'
    LANGUAGE SQL
    IMMUTABLE
    RETURNS NULL ON NULL INPUT;
CREATE OR REPLACE FUNCTION TrimmedCenterline(polyline geometry) RETURNS geometry AS '
    WITH tbla AS (
        SELECT polyline, (ST_Dump(polyline)).geom as line
    ),
    tblb AS (
        SELECT polyline, line as shortestBranchLine
        FROM tbla
        WHERE CountDisconnectedEndpoints(polyline, line) > 0
        ORDER BY ST_Length(line) ASC
        LIMIT 1
    ),
    tblc AS (
        SELECT ST_LineMerge(ST_Difference(polyline, shortestBranchLine)) as polyline
        FROM tblb
    )
    SELECT TrimmedCenterline(polyline) as polyline
    FROM tblc
    WHERE ST_NumGeometries(polyline) > 1
    UNION ALL
    SELECT polyline FROM tblc
;'
    LANGUAGE SQL
    IMMUTABLE
    RETURNS NULL ON NULL INPUT;
CREATE OR REPLACE FUNCTION LabelCenterline(input geometry) RETURNS geometry AS '
    WITH tbla AS (
        SELECT input as polygon WHERE ST_GeometryType(input) = ''ST_Polygon''
        UNION ALL
        SELECT ST_ConcaveHull(input, 0.1) as polygon WHERE ST_GeometryType(input)=''ST_MultiPolygon''
    ),
    tblb AS (
        SELECT ST_MakePolygon(ST_ExteriorRing(polygon)) as polygon
        FROM tbla
    ),
    tblc AS (
        SELECT polygon, (ST_Dump(ST_VoronoiLines(ST_LineInterpolatePoints(ST_Boundary(polygon), 0.0075)))).geom as lines
        FROM tblb
    ),
    tbld AS (
        SELECT ST_LineMerge(ST_Collect(lines)) as polyline
        FROM tblc
        WHERE ST_Contains(polygon, lines)
    )
    SELECT ST_ChaikinSmoothing(ST_SimplifyPreserveTopology(TrimmedCenterline(polyline), 80), 3, false) FROM tbld
;'
    LANGUAGE SQL
    IMMUTABLE
    RETURNS NULL ON NULL INPUT;


