-- LineLabel
SELECT LineLabel(14, 'Foobar', ST_GeomFromText('POINT(0 0)',900913)) AS t_v1;	-- t
SELECT LineLabel(14, 'Foobar', ST_GeomFromText('LINESTRING(0 0, 0 300)',900913)) AS f_v2;	-- f
SELECT LineLabel(15, 'Foobar', ST_GeomFromText('LINESTRING(0 0, 0 300)',900913)) AS t_v3;	-- t
