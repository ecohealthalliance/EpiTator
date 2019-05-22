"""
Script for importing species names from ITIS (https://www.itis.gov/)
into the sqlite synonym table so they can be resolved by the resolved keyword
annotator.
"""
from __future__ import absolute_import
from __future__ import print_function
import sqlite3
from six import BytesIO
from zipfile import ZipFile
from six.moves.urllib import request
from six.moves.urllib_error import URLError
from tempfile import NamedTemporaryFile
import os
import sys
from ..get_database_connection import get_database_connection
from ..utils import batched


ITIS_URL = "https://www.itis.gov/downloads/itisSqlite.zip"


# The data model for the itis database is available here:
# https://www.itis.gov/pdf/ITIS_ConceptualModelEntityDefinition.pdf
def download_itis_database():
    print("Downloading ITIS data from: " + ITIS_URL)
    try:
        url = request.urlopen(ITIS_URL)
    except URLError:
        print("You might be operating behind a proxy. Try adopting your proxy settings.")
        sys.exit(1)
    zipfile = ZipFile(BytesIO(url.read(int(url.headers['content-length']))))
    print("Download complete")
    named_temp_file = NamedTemporaryFile()
    itis_version = zipfile.filelist[0].filename.split('/')[0]
    db_file = None
    for f in zipfile.filelist:
        if f.filename.endswith('.sqlite'):
            db_file = f
            break
    with zipfile.open(db_file) as open_db_file:
        named_temp_file.write(open_db_file.read())
        named_temp_file.flush()
    return named_temp_file, itis_version


def import_species(drop_previous=False):
    connection = get_database_connection(create_database=True)
    cur = connection.cursor()
    if drop_previous:
        print("Removing previous ITIS data...")
        cur.execute("""
        DELETE FROM synonyms WHERE entity_id IN (
            SELECT id FROM entities WHERE source = 'ITIS'
        )""")
        cur.execute("DELETE FROM entities WHERE source = 'ITIS'")
        cur.execute("DELETE FROM metadata WHERE property = 'itis_version'")
    current_itis_version = next(cur.execute("SELECT value FROM metadata WHERE property = 'itis_version'"), None)
    if current_itis_version:
        print("The species data has already been imported. Run this again with --drop-previous to re-import it.")
        return
    if os.environ.get('ITIS_DB_PATH'):
        itis_db_file = open(os.environ.get('ITIS_DB_PATH'))
        itis_version = os.environ.get('ITIS_VERSION')
    else:
        itis_db_file, itis_version = download_itis_database()
    itis_db = sqlite3.connect(itis_db_file.name)
    cur.execute("INSERT INTO metadata VALUES ('itis_version', ?)", (itis_version,))
    itis_cur = itis_db.cursor()
    results = itis_cur.execute("""
    SELECT
      tsn,
      complete_name
    FROM taxonomic_units
    """)
    cur.executemany("INSERT INTO entities VALUES (?, ?, 'species', 'ITIS')", [
        ("tsn:" + str(result[0]), result[1])
        for result in results])
    connection.commit()
    # synonyms_init is a temporary tables that is aggregated to generate the
    # final synonyms table.
    cur.execute("DROP TABLE IF EXISTS synonyms_init")
    cur.execute("""
    CREATE TABLE synonyms_init (
        synonym TEXT, entity_id TEXT, weight INTEGER
    )""")
    insert_command = 'INSERT OR IGNORE INTO synonyms_init VALUES (?, ?, ?)'
    # vern_ref_links and reference_links are used to weight the terms
    query = itis_cur.execute("""
    SELECT
      tsn,
      completename AS name,
      count(documentation_id) AS refs
    FROM longnames
    LEFT JOIN reference_links USING (tsn)
    GROUP BY tsn, completename

    UNION

    SELECT
      tsn,
      vernacular_name AS name,
      count(documentation_id) AS refs
    FROM vernaculars
    LEFT JOIN vern_ref_links USING (tsn)
    GROUP BY tsn, vernacular_name
    """)
    for batch in batched(query):
        tuples = []
        for result in batch:
            tsn, name, refs = [x for x in result]
            if refs >= 3:
                weight = 3
            else:
                weight = refs
            tuples.append((name, 'tsn:' + str(tsn), weight))
        cur.executemany(insert_command, tuples)
    print("Importing hard-coded species names")
    cur.executemany(insert_command, [
        ('man', 'tsn:180092', 3),
        ('men', 'tsn:180092', 3),
        ('woman', 'tsn:180092', 3),
        ('women', 'tsn:180092', 3),
        ('human', 'tsn:180092', 3),
        ('humans', 'tsn:180092', 3),
        ('person', 'tsn:180092', 3),
        ('people', 'tsn:180092', 3),
        # buffalo
        ('buffalo', 'tsn:898079', 3),
        ('buffaloes', 'tsn:898079', 3),
        # chickens
        ('chicken', 'tsn:176086', 3),
        ('chickens', 'tsn:176086', 3),
        ('hen', 'tsn:176086', 3),
        ('rooster', 'tsn:176086', 3),
        # ducks
        ('duck', 'tsn:174983', 3),
        ('ducks', 'tsn:174983', 3),
    ])
    print("Importing synonyms from ITIS database...")
    cur.execute('''
    INSERT INTO synonyms
    SELECT synonym, entity_id, max(weight)
    FROM synonyms_init
    GROUP BY synonym, entity_id
    ''')
    cur.execute("DROP TABLE 'synonyms_init'")
    connection.commit()
    connection.close()
    itis_db_file.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.set_defaults(drop_previous=False)
    args = parser.parse_args()
    import_species(args.drop_previous)
