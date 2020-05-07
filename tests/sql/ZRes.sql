-- ZRes
SELECT round(ZRes(0)::numeric, 4) AS v1;	-- 156543.0339
SELECT round(ZRes(19)::numeric, 4) AS v2;	-- 0.2986
SELECT round(ZRes(0.5)::numeric, 4) AS v3;	-- 110692.6408
SELECT ZRes(NULL) AS null_v4;	-- \\N


