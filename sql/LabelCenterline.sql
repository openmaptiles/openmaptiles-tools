/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates a linestring suitable for a label.

__Parameters:__

- `geometry` inGeometry - A polygon or multipolygon.
- `integer` maxVoronoiVertices - The maximum number of points per polygon of the `geometry` that will be used to calculate the centerline. Lower values will significantly increase execution speed but can result in much less accurate results. Set to `0` to use all points of the input geometry (maximum accuracy). 
- `float` sourceSimplification - The `tolerance` parameter of `ST_SimplifyPreserveTopology`, applied to the polygon before the centerline is calculated. Higher values will increase execution speed but can result in less accurate results. Set to `0` to disable simplification (maximum accuracy).
- `float` simplification - The `tolerance` parameter of `ST_SimplifyPreserveTopology`, applied to the output centerline. Does not appreciably affect performance. Set to `0` to disable simplification.
- `integer` smoothingReps - The number of smoothing iterations to apply to the output centerline. Corresponds to the `nIterations` parameter of `ST_ChaikinSmoothing`. Does not appreciably affect performance. Set to `0` to disable smoothing.

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
CREATE OR REPLACE FUNCTION LabelCenterline(
    inGeometry geometry,
    maxVoronoiVertices integer default 100,
    sourceSimplification float default 0,
    simplification float default 100,
    smoothingReps integer default 3
)
    RETURNS geometry
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH polygons AS (
            SELECT inGeometry AS inPolygon WHERE ST_GeometryType(inGeometry) = 'ST_Polygon'
            UNION ALL
            SELECT (ST_Dump(inGeometry)).geom AS inPolygon WHERE ST_GeometryType(inGeometry)='ST_MultiPolygon'
        ),
        shellPolygons AS (
            SELECT ST_SimplifyPreserveTopology(ST_MakePolygon(ST_ExteriorRing(inPolygon)), sourceSimplification) AS shellPolygon
            FROM polygons
        ),
        shellVertices AS (
            SELECT shellPolygon, ST_LineInterpolatePoints(ST_Boundary(shellPolygon), 1.0/maxVoronoiVertices) as vertices
            FROM shellPolygons
            WHERE maxVoronoiVertices > 0 AND ST_NPoints(shellPolygon) > maxVoronoiVertices
            UNION ALL
            SELECT shellPolygon, ST_Points(shellPolygon) as vertices
            FROM shellPolygons
            WHERE maxVoronoiVertices = 0 OR ST_NPoints(shellPolygon) <= maxVoronoiVertices
        ),
        allVoroniLines AS (
            SELECT shellPolygon, (ST_Dump(ST_VoronoiLines(vertices))).geom AS voroniLines
            FROM shellVertices
        ),
        containedVoroniPolylines AS (
            SELECT ST_LineMerge(ST_Collect(voroniLines)) AS voroniPolyline
            FROM allVoroniLines
            WHERE ST_Contains(shellPolygon, voroniLines)
            GROUP BY shellPolygon
        ),
        simplifedCenterline AS (
            SELECT ST_SimplifyPreserveTopology(ST_Collect(TrimmedCenterline(voroniPolyline)), simplification) AS polyline
            FROM containedVoroniPolylines
        )
        SELECT ST_ChaikinSmoothing(polyline, smoothingReps, false) AS polyline
        FROM simplifedCenterline
        WHERE smoothingReps != 0
        UNION ALL
        SELECT *
        FROM simplifedCenterline
        WHERE smoothingReps = 0;
    END;
