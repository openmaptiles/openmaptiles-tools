/******************************************************************************
### Z ###

Returns a Web Mercator integer zoom level given a scale denominator.

Useful with Mapnik's !scale_denominator! token in vector tile source
queries.

__Parameters:__

- `numeric` scale_denominator - The denominator of the scale, eg `250000`
  for a 1:250,000 scale.

__Returns:__ `integer`

__Example Mapbox Studio query:__

```sql
( SELECT * FROM roads
  WHERE Z(!scale_denominator!) >= 12
) AS data
```
******************************************************************************/
create or replace function z (numeric)
  returns integer
  language sql
  immutable
  parallel safe
  returns null on null input
as $func$
select
  case
    -- Don't bother if the scale is larger than ~zoom level 0
    when $1 > 600000000 or $1 = 0 then null
    else cast (round(log(2,559082264.028/$1)) as integer)
  end;
$func$;


