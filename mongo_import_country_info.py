"""
Import the country code -> country name mapping from countryInfo.txt.

countryInfo data is available here:
http://download.geonames.org/export/dump/
"""
import sys, csv
import unicodecsv
import pymongo
import config
import time

def parse_number(num, default):
    try:
        return int(num)
    except ValueError:
        try:
            return float(num)
        except ValueError:
            return default

def read_country_info_csv(file_path):
    country_info_fields=[
        'ISO',
        'ISO3',
        'ISO-Numeric',
        'fips',
        'Country',
        'Capital',
        'Area(in sq km)',
        'Population',
        'Continent',
        'tld',
        'CurrencyCode',
        'CurrencyName',
        'Phone',
        'Postal Code',
        'Format',
        'Regex',
        'Languages',
        'geonameid',
        'neighbours',
        'EquivalentFipsCode'
    ]

    with open(file_path, 'rb') as f:
        reader = unicodecsv.DictReader(f,
            fieldnames=country_info_fields,
            encoding='utf-8',
            delimiter='\t',
            quoting=csv.QUOTE_NONE)
        for d in reader:
            d['Area(in sq km)'] = parse_number(d['Area(in sq km)'], 0)
            d['Population'] = parse_number(d['Population'], 0)
            print d
            yield d

if __name__ == '__main__':
    print "Loading countryInfo should only take a couple seconds..."
    db = pymongo.Connection(config.mongo_url)['geonames']
    collection = db['countryInfo']
    collection.drop()
    for i, countryInfo in enumerate(read_country_info_csv('countryInfo.txt')):
        collection.insert(countryInfo)
    db.countryInfo.ensure_index('ISO')
    db.countryInfo.ensure_index('Country')

    test_names = ['China', 'British Virgin Islands', 'Netherlands Antilles']
    query = db.countryInfo.find({'Country' : { '$in' : test_names } } )
    found_names = set()
    for countryInfo in query:
        found_names.add(countryInfo['Country'])
    difference = set(test_names) - found_names
    if difference != set():
        print "Test failed!"
        print "Missing countries:", difference
