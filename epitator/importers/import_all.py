"""
Script for importing species names from ITIS (https://www.itis.gov/)
into the sqlite synonym table so they can be resolved by the resolved keyword
annotator.
"""
from __future__ import absolute_import
from __future__ import print_function
from .import_disease_ontology import import_disease_ontology
from .import_species import import_species
from .import_geonames import import_geonames


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.set_defaults(drop_previous=False)
    args = parser.parse_args()
    import_disease_ontology(args.drop_previous)
    import_species(args.drop_previous)
    import_geonames(args.drop_previous)
