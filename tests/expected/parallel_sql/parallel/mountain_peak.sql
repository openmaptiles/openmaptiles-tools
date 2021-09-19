DO $$ BEGIN RAISE NOTICE 'Processing layer mountain_peak'; END$$;

-- Assert my_magic_table exists
do $$
begin
   PERFORM 'my_magic_table'::regclass;
exception when undefined_table then
	RAISE EXCEPTION '%! The required table "my_magic_table" is not existing for the layer "mountain_peak"', SQLERRM;
end;
$$ language 'plpgsql';

-- Assert my_magic_func(TEXT, TEXT) exists
do $$
begin
   PERFORM 'my_magic_func(TEXT, TEXT)'::regprocedure;
exception when undefined_function then
	RAISE EXCEPTION '%! The required function "my_magic_func(TEXT, TEXT)" is not existing for the layer "mountain_peak"', SQLERRM;
when invalid_text_representation then
	RAISE EXCEPTION '%! The arguments of the required function "my_magic_func(TEXT, TEXT)" of the layer "mountain_peak" are missing. Example: "my_magic_func(TEXT, TEXT)(TEXT, TEXT)"', SQLERRM;
end;
$$ language 'plpgsql';

DO $$ BEGIN RAISE NOTICE 'Finished layer mountain_peak'; END$$;
