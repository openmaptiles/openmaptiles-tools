/******************************************************************************
### LabelCenterline ###

Given a polygon or multipolygon, calculates one or more linestrings suitable for labeling.

__Parameters:__

- `geometry` inGeometry - A polygon or multipolygon.
- `integer` maxVoronoiVertices - The maximum number of points per polygon of the `geometry` that will be used to calculate the centerline. Lower values will significantly increase execution speed but can result in much less accurate results. Set to `0` to use all points of the input geometry (maximum accuracy). 
- `float` sourceSimplificationRatio - The `tolerance` parameter of `ST_SimplifyPreserveTopology` as a fraction of the geometry's bounding box, applied to the polygon before the centerline is calculated. Higher values will increase execution speed but can result in less accurate results. Set to `0` to disable simplification (maximum accuracy).
- `float` minSegmentLengthRatio - The minimum length allowed for a branch or independent segment relative to the total length of the output. Set to `1` to return only a single centerline. Set to `0` to include all branches (not recommended). Values between `0.15 and 0.25` tend to have nice results for polygons with multiple "arms".
- `float` minHoleAreaRatio - The minimum area of a hole relative to the total area of the geometry for it to be included. Set to `1` to ignore all holes. Set to `0` to account for all holes.
- `float` simplificationRatio - The `tolerance` parameter of `ST_SimplifyPreserveTopology` as a fraction of the geometry's bounding box, applied to the output centerline. Does not appreciably affect performance. Set to `0` to disable simplification.
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
    sourceSimplificationRatio float default 0.0001,
    minSegmentLengthRatio float default 1, -- 0.175 is a good value if you want to allow a couple big branches
    minHoleAreaRatio float default 1, -- 0.01 has decent results for ignoring all but the largest holes
    simplificationRatio float default 0.02,
    smoothingReps integer default 3
)
    RETURNS geometry
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    BEGIN ATOMIC
        WITH inGeometryInfo AS (
            SELECT LEAST(ST_XMax(inGeometry)-ST_XMin(inGeometry), ST_YMax(inGeometry)-ST_YMin(inGeometry)) AS leastBBoxDimension
        ), simplifiedGeometry AS (
            SELECT ST_MakeValid(ST_Simplify(inGeometry, (SELECT leastBBoxDimension * sourceSimplificationRatio FROM inGeometryInfo), false)) AS inGeometry
        ), polygons AS (
            SELECT inGeometry AS inPolygon
            FROM simplifiedGeometry
            WHERE ST_GeometryType(inGeometry) = 'ST_Polygon'
            UNION ALL
            SELECT (ST_Dump(inGeometry)).geom AS inPolygon
            FROM simplifiedGeometry
            WHERE ST_GeometryType(inGeometry)='ST_MultiPolygon'
        ),
        polygonsSummary AS (
            SELECT inPolygon, ST_Area(Box2D(inPolygon)) AS exteriorRingArea, ST_DumpRings(inPolygon) AS ringInfo
            FROM polygons
        ),
        rings AS (
            SELECT inPolygon, exteriorRingArea, ST_ExteriorRing((ringInfo).geom) AS ring, (ringInfo).path[1] AS ringNum
            FROM polygonsSummary
        ),
        largeEnoughRings AS ( 
            SELECT inPolygon, ring
            FROM rings
            --always keep the exterior ring
            WHERE ringNum = 0
                OR ST_Area(Box2D(ST_LineInterpolatePoints(ring, 0.05))) >= exteriorRingArea * minHoleAreaRatio
        ),
        filteredRings AS ( 
            SELECT *
            FROM largeEnoughRings
            WHERE minHoleAreaRatio < 1
            UNION ALL
            SELECT inPolygon, ST_ExteriorRing(inPolygon) AS ring
            FROM polygons
            WHERE minHoleAreaRatio >= 1
        ),
        preppedRings AS (
            SELECT inPolygon, ring, ST_LineInterpolatePoints(ring, 1.0/maxVoronoiVertices) AS voronoiVertices
            FROM filteredRings
            WHERE maxVoronoiVertices > 0 AND ST_NPoints(ring) > maxVoronoiVertices
            UNION ALL
            SELECT inPolygon, ring, ST_Points(ring) AS voronoiVertices
            FROM filteredRings
            WHERE maxVoronoiVertices = 0 OR ST_NPoints(ring) <= maxVoronoiVertices
        ),
        ringArrays AS (
            SELECT (array_agg(ring)) AS ringArray, ST_Collect(voronoiVertices) AS voronoiVertices
            FROM preppedRings
            GROUP BY inPolygon
        ),
        preppedPolygons AS (
            SELECT ST_MakePolygon(ringArray[1], ringArray[2:]) AS preppedPolygon, voronoiVertices
            FROM ringArrays
        ),
        allVoroniLines AS (
            SELECT preppedPolygon, (ST_Dump(ST_VoronoiLines(voronoiVertices))).geom AS voroniLine
            FROM preppedPolygons
        ),
        containedVoroniPolylines AS (
            SELECT ST_LineMerge(ST_Collect(voroniLine)) AS voroniPolyline
            FROM allVoroniLines
            WHERE ST_Contains(preppedPolygon, voroniLine)
            GROUP BY preppedPolygon
        ),
        centerline AS (
            SELECT ST_Union(TrimmedCenterline(voroniPolyline, minSegmentLengthRatio)) AS polyline
            FROM containedVoroniPolylines
        ),
        simplifedCenterline AS (
            SELECT ST_SimplifyPreserveTopology(polyline, (SELECT leastBBoxDimension*simplificationRatio FROM inGeometryInfo)) AS polyline
            FROM centerline
            WHERE simplificationRatio != 0
            UNION ALL
            SELECT *
            FROM centerline
            WHERE simplificationRatio = 0
        )
        SELECT ST_ChaikinSmoothing(polyline, smoothingReps, true /* preserveEndPoints */) AS polyline
        FROM simplifedCenterline
        WHERE smoothingReps != 0
        UNION ALL
        SELECT *
        FROM simplifedCenterline
        WHERE smoothingReps = 0;
    END;
