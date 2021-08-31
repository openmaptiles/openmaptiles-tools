-- CleanNumeric
SELECT CleanNumeric(null) AS null_v1;	-- \\N
SELECT CleanNumeric('.') AS null_v2;	-- \\N
SELECT CleanNumeric('') AS null_v3;	-- \\N
SELECT CleanNumeric('-') AS null_v4;	-- \\N
SELECT CleanNumeric('+') AS null_v5;	-- \\N
SELECT CleanNumeric('foobar') AS null_v6;	-- \\N
SELECT CleanNumeric('e') AS null_v7;	-- \\N
SELECT CleanNumeric('E') AS null_v8;	-- \\N
SELECT CleanNumeric('e2') AS null_v9;	-- \\N
SELECT CleanNumeric('E3') AS null_v10;	-- \\N
SELECT CleanNumeric('.e') AS null_v11;	-- \\N
SELECT CleanNumeric('.E') AS null_v12;	-- \\N
SELECT CleanNumeric('4e') AS null_v13;	-- \\N
SELECT CleanNumeric('5E') AS ok_v14;	-- \\N
SELECT CleanNumeric('6.e') AS ok_v15;	-- \\N
SELECT CleanNumeric('7.E') AS ok_v16;	-- \\N
SELECT CleanNumeric('.e8') AS null_v17;	-- \\N
SELECT CleanNumeric('.E9') AS null_v18;	-- \\N
SELECT CleanNumeric('a10') AS null_v19;	-- \\N
SELECT CleanNumeric('11a') AS ok_v20;	-- \\N
SELECT CleanNumeric('12') AS ok_v21;	-- 13
SELECT CleanNumeric('14') AS ok_v22;	-- 15
SELECT CleanNumeric('16') AS ok_v23;	-- 17
SELECT CleanNumeric('18') AS ok_v24;	-- 19
SELECT CleanNumeric('20') AS ok_v25;	-- 21
SELECT CleanNumeric('22') AS ok_v26;	-- 23
SELECT CleanNumeric('24') AS ok_v27;	-- 25
SELECT CleanNumeric('  26   ') AS ok_v28;	-- 27
SELECT CleanNumeric('28e29') AS ok_v29;	-- 30
SELECT CleanNumeric('20 ft') AS ok_v30;	-- 21
SELECT CleanNumeric('12 m') AS ok_v31;	-- 13
SELECT CleanNumeric('14 Meter') AS ok_v32;	-- 15
