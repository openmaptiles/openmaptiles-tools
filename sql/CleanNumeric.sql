/******************************************************************************
### CleanNumeric ###

Returns the input text as an numeric if possible, otherwise null.

__Parameters:__

- `text` i - Text that you would like as an numeric.

__Returns:__ `numeric`
******************************************************************************/
create or replace function CleanNumeric (i text) returns numeric as
$body$
 SELECT substring(i from '^\s*([-+]?(?=\d|\.\d)\d*(?:\.\d*)?(?:[Ee][-+]?\d+)?)[\s\w]*$')::numeric;
$body$
language sql
strict immutable cost 20
parallel safe;
