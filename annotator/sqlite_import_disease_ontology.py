"""
Script for importing disease names from the disease ontology (http://disease-ontology.org/)
into the slite synonym table so they can be resolved by the resolved keyword annotator.
"""
import rdflib
import re
from get_database_connection import get_database_connection


def batched(array):
    batch_size = 100
    batch = []
    for idx, item in enumerate(array):
        batch.append(item)
        batch_idx = idx % batch_size
        if batch_idx == batch_size - 1:
            yield batch
            batch = []
    yield batch


def import_disease_ontology(drop_previous=False):
    connection = get_database_connection(create_database=True)
    cur = connection.cursor()
    if drop_previous:
        print "Dropping previous database..."
        cur.execute("DROP TABLE IF EXISTS 'synonyms'")
        cur.execute("DROP TABLE IF EXISTS 'synonyms_init'")
        cur.execute("DROP TABLE IF EXISTS 'entity_labels'")
    table_exists = len(list(cur.execute("""SELECT name FROM sqlite_master
        WHERE type='table' AND name='synonyms'"""))) > 0
    if table_exists:
        print "The table already exists. Run this again with --drop-previous to recreate it."
        return
    # synonyms_init is a temporary tables that is aggregated to generate the
    # final synonyms table.
    cur.execute("""
    CREATE TABLE synonyms_init (
        synonym text, uri text, weight integer
    )""")
    cur.execute("""
    CREATE TABLE synonyms (
        synonym text, uri text, weight integer
    )""")
    i = 0
    insert_command = 'INSERT OR IGNORE INTO synonyms_init VALUES (?, ?, ?)'
    print("Loading disease ontology...")
    disease_ontology = rdflib.Graph()
    disease_ontology.parse(
        "http://purl.obolibrary.org/obo/doid.owl",
        format="xml")
    print("Importing synonyms from disease ontology...")
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
                print "Unknown synonymType:", synonymType
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
    # Extra synonyms not in the disease ontology
    cur.executemany(insert_command, [
        ('HIV', 'http://purl.obolibrary.org/obo/DOID_526', 3),
        ('Ebola', 'http://purl.obolibrary.org/obo/DOID_4325', 3),
        ('EVD', 'http://purl.obolibrary.org/obo/DOID_4325', 3),
    ])
    cur.execute('''
    INSERT INTO synonyms
    SELECT synonym, uri, max(weight)
    FROM synonyms_init
    GROUP BY synonym, uri
    ''')
    disease_labels = disease_ontology.query("""
    SELECT ?entity ?label
    WHERE {
        # only include diseases by infectious agent
        ?entity rdfs:subClassOf* obo:DOID_0050117
        ; rdfs:label ?label
    }
    """)
    cur.execute("""
    CREATE TABLE entity_labels (
        uri text, label text
    )""")
    cur.executemany("INSERT INTO entity_labels VALUES (?, ?)", [
        (str(result[0]), str(result[1]))
        for result in disease_labels])
    cur.execute("DROP TABLE IF EXISTS 'synonyms_init'")
    print "Creating indexes..."
    cur.execute('''
    CREATE INDEX synonym_index
    ON synonyms (synonym);
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
    import_disease_ontology(args.drop_previous)
