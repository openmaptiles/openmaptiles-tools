/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates one or more linestrings suitable for labeling.

__Parameters:__

- `geometry` inGeometry - A polygon or multipolygon.
- `integer` maxVoronoiVertices - The maximum number of points per polygon of the `geometry` that will be used to calculate the centerline. Lower values will significantly increase execution speed but can result in much less accurate results. Set to `0` to use all points of the input geometry (maximum accuracy). 
- `float` sourceSimplification - The `tolerance` parameter of `ST_SimplifyPreserveTopology`, applied to the polygon before the centerline is calculated. Higher values will increase execution speed but can result in less accurate results. Set to `0` to disable simplification (maximum accuracy).
- `float` minSegmentLengthRatio - The minimum length allowed for a branch or independent segment relative to the total length of the output. Set to `1` to return only a single centerline. Set to `0` to include all branches (not recommended). Values between `0.15 and 0.25` tend to have nice results for polygons with multiple "arms".
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
CREATE OR REPLACE FUNCTION TrimmedCenterline(inPolyline geometry, minSegmentLengthRatio float)
    RETURNS geometry
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH edges AS (
            SELECT (ST_Dump(inPolyline)).geom AS edge
        ),
        edgesWithLength AS (
            SELECT edge, ST_Length(edge) AS edgeLength
            FROM edges
        ),
        edgesSummary AS (
           SELECT sum(edgeLength) AS totalEdgeLength FROM edgesWithLength
        ),
        shortestBranchEdge AS (
            SELECT edge
            FROM edgesWithLength
            WHERE CountDisconnectedEndpoints(inPolyline, edge) > 0
                AND edgeLength < (SELECT totalEdgeLength FROM edgesSummary) * minSegmentLengthRatio
            ORDER BY edgeLength ASC
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
        SELECT TrimmedCenterline(polyline, minSegmentLengthRatio) AS polyline
        FROM trimmedPolyline
        WHERE ST_NumGeometries(polyline) > 1
            -- if we didn't trim anything then we're done
            AND ST_NumGeometries(polyline) != ST_NumGeometries(inPolyline)
        UNION ALL
        SELECT polyline FROM trimmedPolyline;
    END;
CREATE OR REPLACE FUNCTION LabelCenterline(
    inGeometry geometry,
    maxVoronoiVertices integer default 100,
    sourceSimplification float default 0,
    minSegmentLengthRatio float default 1, --0.175 is a good value if you want to allow a couple big branches
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
            SELECT shellPolygon, ST_LineInterpolatePoints(ST_Boundary(shellPolygon), 1.0/maxVoronoiVertices) AS vertices
            FROM shellPolygons
            WHERE maxVoronoiVertices > 0 AND ST_NPoints(shellPolygon) > maxVoronoiVertices
            UNION ALL
            SELECT shellPolygon, ST_Points(shellPolygon) AS vertices
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
            SELECT ST_SimplifyPreserveTopology(ST_Union(TrimmedCenterline(voroniPolyline, minSegmentLengthRatio)), simplification) AS polyline
            FROM containedVoroniPolylines
        )
        SELECT ST_ChaikinSmoothing(polyline, smoothingReps, true /* preserveEndPoints */) AS polyline
        FROM simplifedCenterline
        WHERE smoothingReps != 0
        UNION ALL
        SELECT *
        FROM simplifedCenterline
        WHERE smoothingReps = 0;
    END;
