"""
Script for importing labels from wikidata into the sqlite synonym table so
they can be resolved by the resolved keyword annotator.
Currently only animal diseases and hand selected human diseases are imported.
"""
from __future__ import absolute_import
from __future__ import print_function
from ..get_database_connection import get_database_connection
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode
from six.moves.urllib.error import URLError
import json
import datetime
import os


def import_wikidata(drop_previous=False, http_proxy=None, https_proxy=None):
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
    if http_proxy:
        os.environ["HTTP_PROXY"] = http_proxy
    if https_proxy:
        os.environ["HTTPS_PROXY"] = https_proxy
    try:
        response = urlopen("https://query.wikidata.org/sparql", str.encode(urlencode({
            "format": "json",
            "query": """
            SELECT ?item ?itemLabel WHERE {
              ?item wdt:P31 wd:Q9190427.
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
            }
            """
        })))
    except URLError as e:
        print(e)
        print('You might be operating behind a proxy. Try repeating the import '
              'using the --http_proxy and --https_proxy flag')
        return
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
    additional_diseases = [
        ('https://www.wikidata.org/wiki/Q16654806', 'Middle East respiratory syndrome',),
        ('https://www.wikidata.org/wiki/Q1142751', 'Norovirus',),
        ('https://www.wikidata.org/wiki/Q15928531', 'Nipah virus',),
        ('https://www.wikidata.org/wiki/Q18350119', 'Acute flaccid myelitis',),
        ('https://www.wikidata.org/wiki/Q6163830', 'Seoul virus',)]
    cur.executemany("INSERT INTO entities VALUES (?, ?, 'disease', 'Wikidata')", additional_diseases)
    cur.executemany("INSERT INTO synonyms VALUES (?, ?, 3)", [
        (disease_name, uri,) for uri, disease_name in additional_diseases])
    cur.executemany("INSERT INTO synonyms VALUES (?, ?, ?)", [
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
    parser.add_argument("--http_proxy",
                        dest="http_proxy")
    parser.add_argument("--https_proxy",
                        dest="https_proxy")
    parser.set_defaults(drop_previous=False)
    parser.set_defaults(http_proxy=None)
    parser.set_defaults(https_proxy=None)
    args = parser.parse_args()
    import_wikidata(drop_previous=args.drop_previous,
                    http_proxy=args.http_proxy,
                    https_proxy=args.https_proxy)
