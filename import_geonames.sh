#!/bin/bash
wget http://download.geonames.org/export/dump/allCountries.zip
unzip allCountries.zip
rm allCountries.zip
python mongo_import_geonames.py
rm allCountries.txt
