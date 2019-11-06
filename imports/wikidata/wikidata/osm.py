


ID_SELECT = '''
select distinct tags->'wikidata' AS id
from {table}
where tags ? 'wikidata'
'''

PAGE_SELECT = '''
select distinct tags->'wikipedia' AS page
from {table}
where tags ? 'wikipedia' and not tags ? 'wikidata'
'''

def get_ids(tables, cur):
    parts = map(lambda t: ID_SELECT.format(table=t), tables)
    q = 'select t.*'
    q += ' from ((' + ') UNION ('.join(parts) + ')) as t'
    q += ' order by t.id;'

    cur.execute(q)
    ids = list(map(lambda t: t[0], cur.fetchall()))
    return ids

def get_pages(tables, cur):
    parts = map(lambda t: PAGE_SELECT.format(table=t), tables)
    q = 'select t.*'
    q += ' from ((' + ') UNION ('.join(parts) + ')) as t'
    q += ' order by t.page;'

    cur.execute(q)
    pages = list(map(lambda t: t[0], cur.fetchall()))
    return pages
