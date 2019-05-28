"""
Script for importing disease names from the disease ontology (http://disease-ontology.org/)
into the sqlite synonym table so they can be resolved by the resolved keyword
annotator.
"""
from __future__ import absolute_import
from __future__ import print_function
import rdflib
import re
from six.moves.urllib.error import URLError
from ..get_database_connection import get_database_connection
from ..utils import batched


DISEASE_ONTOLOGY_URL = "http://purl.obolibrary.org/obo/doid.owl"


def import_disease_ontology(drop_previous=False, root_uri=None):
    if not root_uri:
        root_uri = "obo:DOID_0050117"
    connection = get_database_connection(create_database=True)
    cur = connection.cursor()
    if drop_previous:
        print("Dropping previous data...")
        cur.execute("""
        DELETE FROM synonyms WHERE entity_id IN (
            SELECT id FROM entities WHERE source = 'Disease Ontology'
        )""")
        cur.execute("DELETE FROM entities WHERE source = 'Disease Ontology'")
        cur.execute("DELETE FROM metadata WHERE property = 'disease_ontology_version'")
    current_version = next(cur.execute("""
    SELECT value FROM metadata WHERE property = 'disease_ontology_version'
    """), None)
    if current_version:
        print("The disease ontology has already been imported. Run this again with --drop-previous to re-import it.")
        return
    # synonyms_init is a temporary tables that is aggregated to generate the
    # final synonyms table.
    cur.execute("DROP TABLE IF EXISTS synonyms_init")
    cur.execute("""
    CREATE TABLE synonyms_init (
        synonym TEXT, entity_id TEXT, weight INTEGER
    )""")
    print("Loading disease ontology...")
    disease_ontology = rdflib.Graph()
    try:
        disease_ontology.parse(DISEASE_ONTOLOGY_URL, format="xml")
    except URLError as e:
        print(e)
        print("You might be operating behind a proxy. Try adopting your proxy settings.")
        return

    # Store disease ontology version
    version_query = disease_ontology.query("""
    SELECT ?version
    WHERE {
        ?s owl:versionIRI ?version
    }
    """)
    disease_ontology_version = str(list(version_query)[0][0])
    cur.execute("INSERT INTO metadata VALUES ('disease_ontology_version', ?)",
                (disease_ontology_version,))

    print("Importing entities from disease ontology...")
    disease_labels = disease_ontology.query("""
    SELECT ?entity ?label
    WHERE {
        # only include diseases by infectious agent
        ?entity rdfs:subClassOf* %s
        ; rdfs:label ?label
    }
    """ % (root_uri,))
    cur.executemany("INSERT INTO entities VALUES (?, ?, 'disease', 'Disease Ontology')", [
        (str(result[0]), str(result[1]))
        for result in disease_labels])

    print("Importing synonyms from disease ontology...")
    insert_command = 'INSERT OR IGNORE INTO synonyms_init VALUES (?, ?, ?)'
    disease_query = disease_ontology.query("""
    SELECT ?entity ?synonym ?synonymType (count(?child) AS ?children)
    WHERE {
        VALUES ?synonymType {
            rdfs:label
            oboInOwl:hasExactSynonym
            oboInOwl:hasRelatedSynonym
            oboInOwl:hasNarrowSynonym
        }
        # only include diseases by infectious agent
        ?entity rdfs:subClassOf* obo:DOID_0050117
        ; ?synonymType ?synonym .
        OPTIONAL {
            ?child rdfs:subClassOf ?entity
        }
    } GROUP BY ?entity ?synonym ?synonymType
    """)
    for batch in batched(disease_query):
        tuples = []
        for result in batch:
            rdict = result.asdict()
            synonymType = rdict['synonymType'].split("#")[1]
            weight = 0
            if synonymType == 'label':
                weight += 3
            elif synonymType == 'hasExactSynonym':
                weight += 2
            elif synonymType == 'hasNarrowSynonym':
                weight += 1
            elif synonymType == 'hasRelatedSynonym':
                weight += 0
            else:
                print("Unknown synonymType:", synonymType)
                continue
            if rdict['children'] == 0:
                # Sometimes parents diseases have as synonyms child disease
                # names. The weight of diseases with no children is boosted
                # so that the most specific entity is used.
                weight += 1
            syn_string = str(rdict['synonym'])
            uri = str(rdict['entity'])
            # Remove text that starts with a bracket
            if re.match(re.compile(r"^(\[|\()", re.I), syn_string):
                continue
            syn_string = re.sub(r"\s*\(.*?\)\s*", " ", syn_string)
            syn_string = re.sub(r"\s*\[.*?\]\s*", " ", syn_string)
            syn_string = syn_string.strip()
            if re.match(re.compile(r"^(or|and)\b", re.I), syn_string):
                continue
            if len(syn_string) == 0:
                continue
            elif len(syn_string) > 6:
                tuples.append((syn_string.lower(), uri, weight))
                tuples.append((syn_string, uri, weight))
            else:
                # Short syn_strings are likely to be acronyms so
                # capitalization is preserved.
                tuples.append((syn_string, uri, weight))
        cur.executemany(insert_command, tuples)
    # Extra synonyms not in the disease ontology.
    cur.executemany(insert_command, [
        ('HIV', 'http://purl.obolibrary.org/obo/DOID_526', 3),
        ('Ebola', 'http://purl.obolibrary.org/obo/DOID_4325', 3),
        ('EVD', 'http://purl.obolibrary.org/obo/DOID_4325', 3),
        ('cVDPV1', 'http://purl.obolibrary.org/obo/DOID_4953', 3),
        ('cVDPV2', 'http://purl.obolibrary.org/obo/DOID_4953', 3),
        ('cVDPV3', 'http://purl.obolibrary.org/obo/DOID_4953', 3),
        ('poliovirus', 'http://purl.obolibrary.org/obo/DOID_4953', 3),
        ('polio', 'http://purl.obolibrary.org/obo/DOID_4953', 3),
        ('CCHF', 'http://purl.obolibrary.org/obo/DOID_12287', 3),
    ])
    cur.execute('''
    INSERT INTO synonyms
    SELECT synonym, entity_id, max(weight)
    FROM synonyms_init
    GROUP BY synonym, entity_id
    ''')
    cur.execute("DROP TABLE IF EXISTS 'synonyms_init'")
    connection.commit()
    connection.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.add_argument("--root-uri", default=None)
    parser.set_defaults(drop_previous=False)
    args = parser.parse_args()
    import_disease_ontology(args.drop_previous, args.root_uri)
