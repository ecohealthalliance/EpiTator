#!/bin/bash
wget http://download.geonames.org/export/dump/allCountries.zip
unzip allCountries.zip
rm allCountries.zip
python mongo_import_geonames.py --mongo_url $MONGO_URL
rm allCountries.txt
