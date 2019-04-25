from __future__ import absolute_import
from __future__ import print_function
import six
import csv
import unicodecsv
import re
import sys
from six import BytesIO
from zipfile import ZipFile
from six.moves.urllib import request
from ..get_database_connection import get_database_connection
from ..utils import parse_number, batched, normalize_text


GEONAMES_ZIP_URL = "http://download.geonames.org/export/dump/allCountries.zip"

geonames_field_mappings = [
    ('geonameid', 'text primary key'),
    ('name', 'text'),
    ('asciiname', 'text'),
    ('alternatenames', None),
    ('latitude', 'real'),
    ('longitude', 'real'),
    ('feature_class', 'text'),
    ('feature_code', 'text'),
    ('country_code', 'text'),
    ('cc2', 'text'),
    ('admin1_code', 'text'),
    ('admin2_code', 'text'),
    ('admin3_code', 'text'),
    ('admin4_code', 'text'),
    ('population', 'integer'),
    ('elevation', None),
    ('dem', None),
    ('timezone', None),
    ('modification_date', None)
]


def read_geonames_csv():
    print("Downloading geoname data from: " + GEONAMES_ZIP_URL)
    url = request.urlopen(GEONAMES_ZIP_URL)
    zipfile = ZipFile(BytesIO(url.read()))
    print("Download complete")
    # Loading geonames data may cause errors without this line:
    csv.field_size_limit(sys.maxint if six.PY2 else six.MAXSIZE)
    with zipfile.open('allCountries.txt') as f:
        reader = unicodecsv.DictReader(f,
                                       fieldnames=[
                                           k for k, v in geonames_field_mappings],
                                       encoding='utf-8',
                                       delimiter='\t',
                                       quoting=csv.QUOTE_NONE)
        for d in reader:
            d['population'] = parse_number(d['population'], 0)
            d['latitude'] = parse_number(d['latitude'], 0)
            d['longitude'] = parse_number(d['longitude'], 0)
            if len(d['alternatenames']) > 0:
                d['alternatenames'] = d['alternatenames'].split(',')
            else:
                d['alternatenames'] = []
            yield d


def import_geonames(drop_previous=False):
    connection = get_database_connection(create_database=True)
    cur = connection.cursor()
    if drop_previous:
        print("Dropping geonames data...")
        cur.execute("""DROP TABLE IF EXISTS 'geonames'""")
        cur.execute("""DROP TABLE IF EXISTS 'alternatenames'""")
        cur.execute("""DROP TABLE IF EXISTS 'alternatename_counts'""")
        cur.execute("""DROP INDEX IF EXISTS 'alternatename_index'""")
        cur.execute("""DROP TABLE IF EXISTS 'adminnames'""")
    table_exists = len(list(cur.execute("""SELECT name FROM sqlite_master
        WHERE type='table' AND name='geonames'"""))) > 0
    if table_exists:
        print("The geonames table already exists. "
              "Run this again with --drop-previous to recreate it.")
        return
    # Create table
    cur.execute("CREATE TABLE geonames (" + ",".join([
        '"' + k + '" ' + sqltype
        for k, sqltype in geonames_field_mappings if sqltype]) + ")")
    cur.execute('''CREATE TABLE alternatenames
                 (geonameid text, alternatename text, alternatename_lemmatized text)''')
    cur.execute('''CREATE TABLE adminnames
                 (name text,
                  country_code text, admin1_code text, admin2_code text, admin3_code text,
                  PRIMARY KEY (country_code, admin1_code, admin2_code, admin3_code))''')
    i = 0
    geonames_insert_command = 'INSERT INTO geonames VALUES (' + ','.join([
        '?' for x, sqltype in geonames_field_mappings if sqltype]) + ')'
    alternatenames_insert_command = 'INSERT INTO alternatenames VALUES (?, ?, ?)'
    adminnames_insert_command = 'INSERT OR IGNORE INTO adminnames VALUES (?, ?, ?, ?, ?)'
    for batch in batched(read_geonames_csv()):
        geoname_tuples = []
        alternatename_tuples = []
        adminname_tuples = []
        for geoname in batch:
            i += 1
            total_row_estimate = 11000000
            if i % (total_row_estimate / 40) == 0:
                print(i, '/', total_row_estimate, '+ geonames imported')
                connection.commit()
            if re.match(r"ADM[1-3]$", geoname['feature_code']) or re.match(r"PCL[IH]$", geoname['feature_code']):
                adminname_tuples.append((
                    geoname['name'],
                    geoname['country_code'],
                    geoname['admin1_code'],
                    geoname['admin2_code'],
                    geoname['admin3_code'],))
            geoname_tuples.append(
                tuple(geoname[field]
                      for field, sqltype in geonames_field_mappings
                      if sqltype))
            for possible_name in set([geoname['name'], geoname['asciiname']] + geoname['alternatenames']):
                normalized_name = normalize_text(possible_name)
                # require at least 2 word characters.
                if re.match(r"(.*\w){2,}", normalized_name):
                    alternatename_tuples.append((
                        geoname['geonameid'],
                        possible_name,
                        normalized_name.lower()))
        cur.executemany(geonames_insert_command, geoname_tuples)
        cur.executemany(alternatenames_insert_command, alternatename_tuples)
        cur.executemany(adminnames_insert_command, adminname_tuples)
    print("Creating indexes...")
    cur.execute('''
    CREATE INDEX alternatename_index
    ON alternatenames (alternatename_lemmatized);
    ''')
    connection.commit()
    cur.execute('''CREATE TABLE alternatename_counts
                 (geonameid text primary key, count integer)''')
    cur.execute('''
    INSERT INTO alternatename_counts
    SELECT geonameid, count(alternatename)
    FROM geonames INNER JOIN alternatenames USING ( geonameid )
    GROUP BY geonameid
    ''')
    connection.commit()
    connection.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.set_defaults(drop_previous=False)
    args = parser.parse_args()
    import_geonames(args.drop_previous)
