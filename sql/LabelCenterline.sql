/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates a linestring suitable for a label.

__Parameters:__

- `geometry` inGeometry - A polygon or multipolygon.

__Returns:__ `geometry(multiline)`
******************************************************************************/
CREATE OR REPLACE FUNCTION CountDisconnectedEndpoints(polyline geometry, testline geometry)
    RETURNS integer AS $$
    BEGIN
        RETURN ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(polyline)))
                    - ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(ST_Difference(polyline, testline))))
                    - ST_NPoints(testline) + 2;
    END
    $$ LANGUAGE plpgsql;
CREATE OR REPLACE FUNCTION TrimmedCenterline(inPolyline geometry)
    RETURNS geometry AS $$
    DECLARE outPolyline geometry;
    BEGIN
        WITH tbla AS (
            SELECT inPolyline as polyline, (ST_Dump(inPolyline)).geom as edge
        ),
        tblb AS (
            SELECT polyline, edge as shortestBranchLine
            FROM tbla
            WHERE CountDisconnectedEndpoints(polyline, edge) > 0
            ORDER BY ST_Length(edge) ASC
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
        SELECT polyline INTO outPolyline FROM tblc;
        RETURN outPolyline;
    END
    $$ LANGUAGE plpgsql;
CREATE OR REPLACE FUNCTION LabelCenterline(inGeometry geometry)
    RETURNS geometry AS $$
    DECLARE outPolyline geometry;
    BEGIN
        WITH tbla AS (
            SELECT inGeometry as inPolygon WHERE ST_GeometryType(inGeometry) = 'ST_Polygon'
            UNION ALL
            SELECT ST_ConcaveHull(ST_Points(ST_Simplify(inGeometry, 25)), 0.2) as inPolygon WHERE ST_GeometryType(inGeometry)='ST_MultiPolygon'
        ),
        tblb AS (
            SELECT ST_MakePolygon(ST_ExteriorRing(inPolygon)) as shellPolygon
            FROM tbla
        ),
        tblc AS (
            SELECT shellPolygon, (ST_Dump(ST_VoronoiLines(ST_LineInterpolatePoints(ST_Boundary(shellPolygon), 0.0075)))).geom as voroniLines
            FROM tblb
        ),
        tbld AS (
            SELECT ST_LineMerge(ST_Collect(voroniLines)) as voroniPolyline
            FROM tblc
            WHERE ST_Contains(shellPolygon, voroniLines)
        )
        SELECT ST_ChaikinSmoothing(ST_SimplifyPreserveTopology(TrimmedCenterline(voroniPolyline), 80), 3, false) INTO outPolyline FROM tbld;
        RETURN outPolyline;
    END
    $$ LANGUAGE plpgsql;
