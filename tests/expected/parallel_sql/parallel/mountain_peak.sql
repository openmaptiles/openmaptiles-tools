DO $$ BEGIN RAISE NOTICE 'Processing layer mountain_peak'; END$$;

DO $$ BEGIN
    PERFORM 'my_magic_table'::regclass;
EXCEPTION
    WHEN undefined_table THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'this table or view is required for layer "mountain_peak"';
END;
$$ LANGUAGE 'plpgsql';

DO $$ BEGIN
    PERFORM 'my_magic_func(TEXT, TEXT)'::regprocedure;
EXCEPTION
    WHEN undefined_function THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'this function is required for layer "mountain_peak"';
    WHEN invalid_text_representation THEN
        RAISE EXCEPTION '%', SQLERRM
            USING DETAIL = 'Required function "my_magic_func(TEXT, TEXT)" in layer "mountain_peak" is incorrectly declared. Use full function signature with parameter types, e.g. "my_magic_func(TEXT, TEXT)"';
END;
$$ LANGUAGE 'plpgsql';

DO $$ BEGIN RAISE NOTICE 'Finished layer mountain_peak'; END$$;
