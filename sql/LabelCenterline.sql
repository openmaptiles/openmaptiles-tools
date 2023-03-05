/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates a linestring suitable for a label.

__Parameters:__

- `geometry` inGeometry - A polygon or multipolygon.

__Returns:__ `geometry(multiline)`
******************************************************************************/
CREATE OR REPLACE FUNCTION CountDisconnectedEndpoints(polyline geometry, testline geometry)
    RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH linesExceptTestline AS (
            SELECT (ST_Dump(polyline)).geom AS linestring
            EXCEPT
            SELECT testline AS linestring
        )
        SELECT ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(polyline)))
                    - ST_NPoints(ST_RemoveRepeatedPoints(ST_Points(ST_Collect(linestring))))
                    - ST_NPoints(testline) + 2 FROM linesExceptTestline;
    END;
CREATE OR REPLACE FUNCTION TrimmedCenterline(inPolyline geometry)
    RETURNS geometry
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH edges AS (
            SELECT (ST_Dump(inPolyline)).geom AS edge
        ),
        shortestBranchEdge AS (
            SELECT *
            FROM edges
            WHERE CountDisconnectedEndpoints(inPolyline, edge) > 0
            ORDER BY ST_Length(edge) ASC
            LIMIT 1
        ),
        edgesWithoutShortestBranch AS (
            SELECT * FROM edges
            EXCEPT
            SELECT * FROM shortestBranchEdge
        ),
        trimmedPolyline AS (
            SELECT ST_LineMerge(ST_Collect(edge)) AS polyline
            FROM edgesWithoutShortestBranch
        )
        SELECT TrimmedCenterline(polyline) AS polyline
        FROM trimmedPolyline
        WHERE ST_NumGeometries(polyline) > 1
        UNION ALL
        SELECT polyline FROM trimmedPolyline;
    END;
CREATE OR REPLACE FUNCTION LabelCenterline(inGeometry geometry)
    RETURNS geometry
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH polygons AS (
            SELECT inGeometry AS inPolygon WHERE ST_GeometryType(inGeometry) = 'ST_Polygon'
            UNION ALL
            SELECT (ST_Dump(inGeometry)).geom AS inPolygon WHERE ST_GeometryType(inGeometry)='ST_MultiPolygon'
        ),
        shellPolygons AS (
            SELECT ST_MakePolygon(ST_ExteriorRing(inPolygon)) AS shellPolygon
            FROM polygons
        ),
        allVoroniLines AS (
            SELECT shellPolygon, (ST_Dump(ST_VoronoiLines(ST_LineInterpolatePoints(ST_Boundary(shellPolygon), 0.0075)))).geom AS voroniLines
            FROM shellPolygons
        ),
        containedVoroniPolylines AS (
            SELECT ST_LineMerge(ST_Collect(voroniLines)) AS voroniPolyline
            FROM allVoroniLines
            WHERE ST_Contains(shellPolygon, voroniLines)
            GROUP BY shellPolygon
        )
        SELECT ST_ChaikinSmoothing(ST_SimplifyPreserveTopology(ST_Collect(TrimmedCenterline(voroniPolyline)), 80), 3, false) AS trimmedPolyline
        FROM containedVoroniPolylines;
    END;
