#!/usr/bin/env python
import gzip
import traceback
import json
import re
from multiprocessing import Pool
from collections import defaultdict
from sortedcontainers import SortedList

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
            if line.endswith(b",\n"):
                item = json.loads(line[:-2].decode('utf-8'))
            else:
                item = json.loads(line.decode('utf-8'))
            return item
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            print(line)

def get_id(line):
    prefix = '{"type":"item","id":"'
    prefix_len = len(prefix)
    part = line[prefix_len:(prefix_len+20)]
    if(part and line.startswith(prefix)):
        m = re.search('^(Q[0-9]+)"', part)
        if(m is not None):
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
    ids = SortedList(ids)

    total_ids_len = len(ids)
    # print('finding {} ids'.format(total_ids_len))

    found_ids = []
    with gzip.open(file, 'rb') as f:
        i = 1
        for line in f:
            # search ID
            line = line.decode("utf-8")
            id = get_id(line)
            if id in ids:
                item = get_json(line)
                osm_labels = to_osm_names(item['labels'])
                cur.execute("INSERT INTO {table} (id, labels) VALUES (%s, "
                            "%s)".format(table=table_name), (id, osm_labels))
                found_ids.append(id)
                ids.remove(id)
                if(len(ids) == 0):
                    break

            if i % 100000 == 0:
                conn.commit()
                print('  parsed {:,} lines, already loaded {:,} of {:,}'
                      ' IDs'.format(i, len(found_ids), total_ids_len))
            if i >= limit:
                print('  limit of {:,} parsed lines reached, parsing '
                      'stopped'.format(limit))
                break
            i += 1

    conn.commit()
    print('Loaded {:,} of {:,} Wikidata IDs'.format(len(found_ids),
                                                    total_ids_len))


def get_page(item, pages):
    if 'sitelinks' not in item:
        return None
    for lang in pages:
        key = lang+'wiki'
        if key in item['sitelinks']:
            title = item['sitelinks'][key]['title']
            if title in pages[lang]:
                return (lang, title)
    return None

def multi_parse(file, ids, pages, cur, conn, table_name, limit):
    ids, pages = remove_duplicate_ids_and_pages(ids, pages)
    ids = SortedList(ids)

    total_ids_len = len(ids)
    # print('finding {} ids'.format(total_ids_len))
    total_pages_len = len(pages)
    # print('finding {} pages'.format(total_pages_len))

    pages_bucket = defaultdict(SortedList)
    for page in pages:
        page_parts = page.split(':')
        if(len(page_parts)==2):
            pages_bucket[page_parts[0]].add(page_parts[1])
            # pages_bucket[page_parts[0]].add(page_parts[1].decode('utf8'))
    pool = Pool()

    found_ids = []
    found_pages = []
    parsed_lines = [0]

    def process_json(item):
        try:
            parsed_lines[0] += 1
            if(item is not None):
                id = item['id']
                if id in ids:
                    osm_labels = to_osm_names(item['labels'])
                    cur.execute("INSERT INTO {table} (id, labels) VALUES (%s, "
                                "%s)".format(table=table_name), (id, osm_labels))
                    found_ids.append(id)
                    ids.remove(id)
                else:
                    page_tuple = get_page(item, pages_bucket)
                    if(page_tuple is not None):
                        page = ':'.join(page_tuple)
                        osm_labels = to_osm_names(item['labels'])
                        cur.execute("INSERT INTO {table} (page, labels) VALUES ("
                                    "%s, %s)".format(table=table_name),
                                    (page, osm_labels))
                        found_pages.append(page)
                        lang = page_tuple[0]
                        title = page_tuple[1]
                        pages_bucket[lang].remove(title)
                        if(len(pages_bucket[lang])==0):
                            print('Deleting lang', lang)
                            del pages_bucket[lang]
            if parsed_lines[0] % 10000 == 0:
                conn.commit()
                print('  parsed {:,} lines, already loaded {:,} of {:,}'
                      ' IDs and {:,} of {:,} pages'.format(parsed_lines[0],
                                                           len(found_ids),
                                                           total_ids_len,
                                                           len(found_pages),
                                                           total_pages_len))
            return None
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            print(line)

    with gzip.open(file, 'rb') as f:
        i = 1
        for line in f:
            # item = get_json(line)
            # process_json(item)
            pool.apply_async(get_json, (line,), callback=process_json)

            if i % 10000 == 0:
                print('  read {:,} lines'.format(i))
            if i >= limit:
                print('  limit of {:,} read lines reached, reading '
                      'stopped'.format(limit))
                break
            i += 1
    pool.close()
    pool.join()
    print('Parsed {:,} lines.', parsed_lines[0])

    conn.commit()
    print('Loaded {:,} of {:,} Wikidata IDs and {:,} of {:,} Wikipedia pages'
          ''.format(len(found_ids), total_ids_len, len(found_pages),
                    total_pages_len))
