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
from .import_wikidata import import_wikidata


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--drop-previous", dest='drop_previous', action='store_true')
    parser.add_argument(
        "--accept-licenses", dest='accept_licenses', action='store_true')
    parser.add_argument("--http_proxy",
                        dest="http_proxy")
    parser.add_argument("--https_proxy",
                        dest="https_proxy")
    parser.set_defaults(drop_previous=False)
    parser.set_defaults(http_proxy=None)
    parser.set_defaults(https_proxy=None)
    args = parser.parse_args()
    import_disease_ontology(drop_previous=args.drop_previous,
                            http_proxy=args.http_proxy,
                            https_proxy=args.https_proxy)
    import_species(drop_previous=args.drop_previous,
                   http_proxy=args.http_proxy,
                   https_proxy=args.https_proxy)
    import_geonames(drop_previous=args.drop_previous,
                    http_proxy=args.http_proxy,
                    https_proxy=args.https_proxy)
    import_wikidata(drop_previous=args.drop_previous,
                    http_proxy=args.http_proxy,
                    https_proxy=args.https_proxy)
