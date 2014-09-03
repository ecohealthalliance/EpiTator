#!/bin/bash
wget http://download.geonames.org/export/dump/allCountries.zip
wget http://download.geonames.org/export/dump/countryInfo.txt
unzip allCountries.zip -d diagnosis
rm allCountries.zip
cd diagnosis && python mongo_import_country_info.py && python mongo_import_geonames.py
rm allCountries.txt
rm countryInfo.txt
cd ..
