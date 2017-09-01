#!/usr/bin/env python
import gzip
import traceback
import json
import re
from multiprocessing import Pool
import psycopg2
import psycopg2.extras

POSTGRES_DB='openmaptiles'
POSTGRES_USER='openmaptiles'
POSTGRES_PASSWORD='openmaptiles'
# POSTGRES_HOST=postgres
POSTGRES_HOST='localhost'
POSTGRES_PORT=5432


TABLE_NAME = 'wd_names'

RECREATE_TABLE = """
DROP TABLE IF EXISTS {table};
CREATE TABLE {table} (
    id          varchar(20) UNIQUE,
    page          varchar(200) UNIQUE,
    labels      hstore
);
""".format(table=TABLE_NAME)

# select tags->'wikidata'
# from osm_city_point
# where tags ? 'wikidata';
IDS = ["Q1992389", "Q835835", "Q990125", "Q234178", "Q213154", "Q1235510",
       "Q101254", "Q1024900", "Q2297559", "Q39480", "Q1021164", "Q1072019",
       "Q548248", "Q527467", "Q3404510", "Q319710", "Q3400567", "Q3400273",
       "Q16897705", "Q16214334", "Q6661439", "Q744944", "Q7534635", "Q6661768",
       "Q996492", "Q990153", "Q2003342", "Q752762", "Q5141668", "Q3402241",
       "Q6497774", "Q2243637", "Q5116688", "Q880986", "Q2355142", "Q7852544",
       "Q1774850", "Q427792", "Q319369", "Q1537181", "Q3404407", "Q4787855",
       "Q13644927", "Q3812313", "Q3878305", "Q2741540", "Q3400150", "Q5140509",
       "Q322", "Q23051", "Q10690", ]

# select tags->'wikipedia'
# from osm_city_point
# where tags ? 'wikipedia' and not tags ? 'wikidata';
PAGES = ["en:Caldicot, Monmouthshire", "en:Tenby",
         "en:Pembroke, Pembrokeshire", "en:Mold, Flintshire", "en:Caerphilly",
         "en:Barry, Vale of Glamorgan", "en:Monmouth", "en:Porthmadog",
         "en:Flint, Flintshire", "en:Buckley", "en:Rhuddlan", "en:Rhyl",
         "en:Killay, Swansea", "en:Uplands, Swansea", "en:Southgate, Swansea",
         "en:Barmouth", "en:Llanarth, Ceredigion", "en:Glasbury",
         "en:Knighton, Powys", "en:Dyserth", "en:Llantrisant, Monmouthshire",
         "en:Usk", "en:Dolanog", "en:Bishopston, Swansea",
         "en:Kittle, Swansea", "en:Newton, Swansea", "en:Overton, Swansea",
         "en:Llysworney", "en:Sully, Vale of Glamorgan", "en:Newtown, Powys",
         "en:Three Crosses, Gower", "en:Canton, Cardiff", "en:Llanwrda",
         "en:Tycroes", "en:Brockweir", "en:Tintern", "en:Wrexham",
         "en:Llangynwyd", "en:Maesgeirchen", "en:Wyesham", "en:Aberthin",
         "en:Abermagwr", "en:Meliden", "en:Craig-y-Don", "en:Abercwmboi",
         "en:Redbrook", "en:Abersychan", "en:Overmonnow",
         "en:Great Manson Farm, Monmouth", "en:Buckholt, Monmouthshire",
         "en:Trefeca", "en:Gwytherin", "en:Bonvilston", "en:Miskin",
         "en:Llantrisant", "en:Osbaston, Monmouth", "en:Glanamman",
         "en:Garnant", "en:Carmel, Carmarthenshire", "en:Ffos-y-ffin",
         "en:Llwyncelyn", "en:Betws yn Rhos", "en:Llangernyw",
         "en:Llansadwrn, Anglesey", "en:Bethel, Gwynedd", "en:Caeathro",
         "en:Bodfari", "en:Clawddnewydd", "en:Prestatyn", "en:Llangyndeyrn",
         "en:Pwllgwaelod", "en:St Davids", "en:Clynderwen", "en:Yspyty-Cynfyn",
         "en:Aberfan", "en:Merthyr_Vale", "en:St Clears", ]

DUMP = 'data/latest-all.json.gz'

LIMIT = 100000000
# LIMIT = 100000

def recreate_table(cur):
    cur.execute(RECREATE_TABLE)

def get_json(line):
    if line != "[\n" and line != "]" and line != "]\n" and len(line) > 2:
        try:
            if line.endswith(",\n"):
                # print 'endswith \\n'
                item = json.loads(line[:-2])
            else:
                print 'endswithout \\n'
                item = json.loads(line)
            return item
        except Exception as e:
            print e.message
            print traceback.format_exc()
            print line

def get_id(line):
    prefix = '{"type":"item","id":"'
    prefix_len = len(prefix)
    part = line[prefix_len:(prefix_len+20)]
    if(part and line.startswith(prefix)):
        m = re.search('^(Q[0-9]+)"', part)
        if(m is None):
            print 'NONE LINE'
            print line
        return m.group(1)


def simple_read(file, ids):
    with gzip.open(file, 'rb') as f:
        i = 1
        for line in f:
            # print get_id2(line)

            if i % 10000 == 0:
                print i
            if i >= LIMIT:
                break
            i += 1


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

def simple_parse(file, ids, pages, cur, conn):
    ids, pages = remove_duplicate_ids_and_pages(ids, pages)

    total_ids_len = len(ids)
    print('finding {} ids'.format(total_ids_len))
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
            id = get_id(line)
            if id in ids:
                entity = get_json(line)
                # print entity['sitelinks']
                osm_labels = to_osm_names(entity['labels'])
                cur.execute("INSERT INTO {table} (id, labels) VALUES (%s, "
                            "%s)".format(table=TABLE_NAME), (id, osm_labels))
                conn.commit()
                found_ids.append(id)
                ids.remove(id)
                print('found id {}, already found {} of {} ids'.format(id, len(found_ids), total_ids_len))
                if(len(ids) == 0):
                    break

            # search page
            # if any(raw_page in line for raw_page in raw_pages):
            #     entity = get_json(line)
            #     osm_labels = to_osm_names(entity['labels'])
            #     print('PAGE FOUND')
            #     print osm_labels


            if i % 10000 == 0:
                print i
            if i >= LIMIT:
                break
            i += 1

    print('found {} of {} ids'.format(len(found_ids), total_ids_len))


conn = psycopg2.connect(dbname=POSTGRES_DB, user=POSTGRES_USER,
                        password=POSTGRES_PASSWORD, host=POSTGRES_HOST,
                        port=POSTGRES_PORT)
cur = conn.cursor()
recreate_table(cur)
conn.commit()
psycopg2.extras.register_hstore(conn)
simple_parse(DUMP, IDS, PAGES, cur, conn)
cur.close()
conn.close()
