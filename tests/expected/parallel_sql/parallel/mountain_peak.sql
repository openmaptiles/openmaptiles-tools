DO $$ BEGIN RAISE NOTICE 'Processing layer mountain_peak'; END$$;

-- Assert my_magic_table exists
SELECT 'my_magic_table'::regclass;

-- Assert my_magic_func(TEXT, TEXT) exists
SELECT 'my_magic_func(TEXT, TEXT)'::regprocedure;

DO $$ BEGIN RAISE NOTICE 'Finished layer mountain_peak'; END$$;
