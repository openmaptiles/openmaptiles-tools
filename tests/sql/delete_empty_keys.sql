-- delete_empty_keys
SELECT delete_empty_keys(NULL) AS v1_null;
SELECT delete_empty_keys(''::hstore) AS v2_null;
SELECT delete_empty_keys('"empty"=>""'::hstore) AS v3_null;
SELECT delete_empty_keys('"foo"=>"bar"'::hstore) AS v4;
SELECT delete_empty_keys('"foo"=>"bar", "empty"=>""'::hstore) AS v5;
SELECT delete_empty_keys('"foo"=>"bar", "empty"=>"", "xx"=>"zz"'::hstore) AS v6;
SELECT delete_empty_keys('"empty"=>"", "foo"=>"bar"'::hstore) AS v7;
SELECT delete_empty_keys('""=>"empty_key"'::hstore) AS v8;
SELECT delete_empty_keys('"nil"=>NULL, "foo"=>"bar"'::hstore) AS v9;
SELECT delete_empty_keys('"nil"=>NULL'::hstore) AS v10_null;
