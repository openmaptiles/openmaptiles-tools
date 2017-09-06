#!/usr/bin/env python
import gzip
import traceback
import json
import re

EMPTY_TABLE = """
CREATE TABLE IF NOT EXISTS {table} (
    id          varchar(20) UNIQUE,
    page          varchar(200) UNIQUE,
    labels      hstore
);
TRUNCATE {table};
"""

def empty_table(table, cur):
    cur.execute(EMPTY_TABLE.format(table=table))

def get_json(line):
    if line != "[\n" and line != "]" and line != "]\n" and len(line) > 2:
        try:
            if line.endswith(",\n"):
                # print 'endswith \\n'
                item = json.loads(line[:-2])
            else:
                print('endswithout \\n')
                item = json.loads(line)
            return item
        except Exception as e:
            print(e.message)
            print(traceback.format_exc())
            print(line)

def get_id(line):
    prefix = '{"type":"item","id":"'
    prefix_len = len(prefix)
    part = line[prefix_len:(prefix_len+20)]
    if(part and line.startswith(prefix)):
        m = re.search('^(Q[0-9]+)"', part)
        if(m is None):
            print('NONE LINE')
            print(line)
        return m.group(1)


def to_osm_names(wd_names):
    res = {}
    for lang in wd_names:
        name = wd_names[lang]
        if (lang != name['language']):
            continue
        res['name:'+lang] = name['value']
    return res


def remove_duplicate_ids_and_pages(ids, pages):
    orig_ids_len = len(ids)
    ids = list(set(ids))
    if(len(ids) != orig_ids_len):
        print('ignoring {} duplicate ids'.format(orig_ids_len - len(ids)))

    orig_pages_len = len(pages)
    pages = list(set(pages))
    if(len(pages) != orig_pages_len):
        print('ignoring {} duplicate pages'.format(orig_pages_len - len(
            pages)))

    return (ids, pages)

def simple_parse(file, ids, pages, cur, conn, table_name, limit):
    ids, pages = remove_duplicate_ids_and_pages(ids, pages)

    total_ids_len = len(ids)
    # print('finding {} ids'.format(total_ids_len))
    # total_pages_len = len(pages)
    # print('finding {} pages'.format(total_pages_len))

    # def to_raw(page):
    #     parts = page.split(':')
    #     return '"{lang}wiki":{{"site":"{lang}wiki","title":"{title}"'.format(
    #         lang=parts[0], title=parts[1])
    # raw_pages = map(to_raw, pages)

    found_ids = []
    with gzip.open(file, 'rb') as f:
        i = 1
        for line in f:
            # search ID
            line = line.decode("utf-8")
            id = get_id(line)
            if id in ids:
                entity = get_json(line)
                # print entity['sitelinks']
                osm_labels = to_osm_names(entity['labels'])
                cur.execute("INSERT INTO {table} (id, labels) VALUES (%s, "
                            "%s)".format(table=table_name), (id, osm_labels))
                conn.commit()
                found_ids.append(id)
                ids.remove(id)
                if(len(ids) == 0):
                    break

            # search page
            # if any(raw_page in line for raw_page in raw_pages):
            #     entity = get_json(line)
            #     osm_labels = to_osm_names(entity['labels'])
            #     print('PAGE FOUND')
            #     print osm_labels


            if i % 100000 == 0:
                print('  parsed {:,} lines, already loaded {:,} of {:,}'
                      ' IDs'.format(i, len(found_ids), total_ids_len))
            if i >= limit:
                print('  limit of {:,} parsed lines reached, parsing '
                      'stopped'.format(limit))
                break
            i += 1

    print('Loaded {:,} of {:,} Wikidata IDs'.format(len(found_ids),
                                                    total_ids_len))


