"""
Script for importing labels from wikidata into the sqlite synonym table so
they can be resolved by the resolved keyword annotator.
Currently only animal diseases are imported.
"""
from __future__ import absolute_import
from __future__ import print_function
from ..get_database_connection import get_database_connection
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode
import json
import datetime


def import_wikidata(drop_previous=False):
    connection = get_database_connection(create_database=True)
    cur = connection.cursor()
    if drop_previous:
        print("Dropping previous data...")
        cur.execute("""
        DELETE FROM synonyms WHERE entity_id IN (
            SELECT id FROM entities WHERE source = 'Wikidata'
        )""")
        cur.execute("DELETE FROM entities WHERE source = 'Wikidata'")
        cur.execute("DELETE FROM metadata WHERE property = 'wikidata_retrieval_date'")
    wikidata_retrieval_date = next(cur.execute("""
    SELECT value FROM metadata WHERE property = 'wikidata_retrieval_date'
    """), None)
    if wikidata_retrieval_date:
        print("Wikidata data has already been imported. Run this again with --drop-previous to re-import it.")
        return
    cur.execute("INSERT INTO metadata VALUES ('wikidata_retrieval_date', ?)",
                (datetime.date.today().isoformat(),))
    response = urlopen("https://query.wikidata.org/sparql", urlencode({
        "format": "json",
        "query": """
        SELECT ?item ?itemLabel WHERE {
          ?item wdt:P31 wd:Q9190427.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }
        """
    }))
    results = json.loads(response.read())['results']['bindings']
    print("Importing synonyms...")
    cur.executemany("INSERT INTO entities VALUES (?, ?, 'disease', 'Wikidata')", [
        (result['item']['value'], result['itemLabel']['value'])
        for result in results])
    cur.executemany("INSERT INTO synonyms VALUES (?, ?, 1)", [
        (result['itemLabel']['value'], result['item']['value'])
        for result in results])
    print("Importing manually added diseases not in disease ontology...")
    # Wikidata entities are used in place of those from the disease ontology.
    cur.execute("""
                INSERT INTO entities VALUES
                ('https://www.wikidata.org/wiki/Q16654806',
                 'Middle East respiratory syndrome',
                 'disease', 'Wikidata'
                )""")
    cur.executemany("INSERT INTO synonyms VALUES (?, ?, ?)", [
        ('Middle East respiratory syndrome', 'https://www.wikidata.org/wiki/Q16654806', 3),
        ('MERS', 'https://www.wikidata.org/wiki/Q16654806', 3),
        ('Middle East respiratory syndrome coronavirus', 'https://www.wikidata.org/wiki/Q16654806', 3),
        ('MERS-CoV', 'https://www.wikidata.org/wiki/Q16654806', 3),
    ])
    connection.commit()
    connection.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.set_defaults(drop_previous=False)
    args = parser.parse_args()
    import_wikidata(args.drop_previous)
