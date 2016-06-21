"""
Load mongo database with keywords for annie annotation.
The keyword_array pickle is packaged with the GRITS classifier.
"""
import sys
import re
import pickle
from pymongo import MongoClient

def load_keyword_array(file_path):
    with open(file_path) as f:
        keyword_array = pickle.load(f)
    return keyword_array

def insert_set(names_set, collection):
    """Insert a list of names into a collection"""

    for name in names_set:
        collection.insert({'_id': name})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mongo_url", default='localhost'
    )
    parser.add_argument(
        "--db_name", default='annotation'
    )
    args = parser.parse_args()
    client = MongoClient(args.mongo_url)
    db = client[args.db_name]

    category_labels = {
        'doid/diseases': 'diseases',
        'eha/disease': 'diseases',
        'pm/disease':  'diseases',
        'hm/disease': 'diseases',
        'biocaster/diseases': 'diseases',
        'eha/symptom': 'symptoms',
        'biocaster/symptoms': 'symptoms',
        'doid/has_symptom': 'symptoms',
        'pm/symptom': 'symptoms',
        'symp/symptoms': 'symptoms',
        'wordnet/hosts': 'hosts',
        'eha/vector': 'hosts',
        'wordnet/pathogens': 'pathogens',
        'biocaster/pathogens': 'pathogens',
        'pm/mode of transmission': 'modes',
        'doid/transmitted_by': 'modes',
        'eha/mode of transmission': 'modes'
    }

    collection_labels = set(category_labels.values())
    for collection in collection_labels:
        db[collection].drop()

    keyword_array = load_keyword_array('current_classifier/keyword_array.p')

    for keyword in keyword_array:
        if keyword['category'] in category_labels:
            collection = category_labels[keyword['category']]

            db[collection].find_one_and_replace({'_id': keyword['keyword']}, {
                '_id': keyword['keyword'],
                'source': keyword['category'],
                'linked_keywords': keyword['linked_keywords'],
                'case_sensitive': keyword['case_sensitive']
            }, upsert=True)
