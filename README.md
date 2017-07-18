# EpiTator

Annotators for extracting epidemiological information from text.

## Annotators

### Geoname Annotator

The geoname annotator uses the geonames.org dataset to resolve mentions of geonames.
A classifier is used to disambiguate geonames and rule out false positives.

To use the geoname annotator run the following command to import geonames.org
data into epitator's embedded sqlite3 database:

You should review the geonames license before using this data.

```
python -m epitator.importers.import_geonames
```

#### Usage

```python
from epitator.annotator import AnnoDoc
from epitator.geoname_annotator import GeonameAnnotator
doc = AnnoDoc("Where is Chiang Mai?")
doc.add_tier(GeonameAnnotator())
annotations = doc.tiers["geonames"].spans
geoname = annotations[0].geoname
geoname['name']
# = 'Chiang Mai'
geoname['geonameid']
# = '1153671'
geoname['latitude']
# = 18.79038
geoname['longitude']
# = 98.98468
```

### Resolved Keyword Annotator

The resolved keyword annotator uses an sqlite database of entities to resolve
mentions of multiple synonyms for an entity to a single id.
This project includes scripts for importing diseases and animal species into
that database. The following commands cab be used to invoke them:

The scripts import data from the [Disease Ontology](http://disease-ontology.org/) and [ITIS](https://www.itis.gov/).
You should review their licenses and terms of use before using this data.
Currently the Disease Ontology is under public domain and ITIS requests citation.

```
python -m epitator.importers.import_species
python -m epitator.importers.import_disease_ontology
```

#### Usage

```python
from epitator.annotator import AnnoDoc
from epitator.resolved_keyword_annotator import ResolvedKeywordAnnotator
doc = AnnoDoc("5 cases of smallpox")
doc.add_tier(ResolvedKeywordAnnotator())
annotations = doc.tiers["resolved_keywords"].spans
annotations[0].resolutions
# = [{'uri': u'http://purl.obolibrary.org/obo/DOID_8736', 'weight': 3, 'label': u'smallpox'}]
```

### Count Annotator

The count annotator identifies counts, and case counts in particular.
The count's value is extracted and parsed. Attributes such as whether the count
refers to cases or deaths, or whether the value is approximate are also extracted.

#### Usage

```python
from epitator.annotator import AnnoDoc
from epitator.count_annotator import CountAnnotator
doc = AnnoDoc("5 cases of smallpox")
doc.add_tier(CountAnnotator())
annotations = doc.tiers["counts"].spans
annotations[0].metadata
# = {'count': 5, 'text': '5 cases', 'attributes': ['case']}
```

### Date Annotator

The date annotator identifies and parses dates and date ranges.
All dates are parsed into datetime ranges. For instance, a date like "11-6-87"
would be parsed as a range from the start of the day to the start of the next day,
while a month like "December 2011" would be parsed as a range from the start
of December 1st to the start of the next month.

#### Usage

```python
from epitator.annotator import AnnoDoc
from epitator.date_annotator import DateAnnotator
doc = AnnoDoc("From March 5 until April 7 1988")
doc.add_tier(DateAnnotator())
annotations = doc.tiers["dates"].spans
annotations[0].datetime_range
# = [datetime.datetime(1988, 3, 5, 0, 0), datetime.datetime(1988, 4, 7, 0, 0)]
```

### JVM-NLP Annotator

The jvm_nl_annotator relies on a server from this project to create annotations using Stanford's NLP library:

https://github.com/ecohealthalliance/jvm-nlp

The AnnoTiers it creates include tokens, sentences, pos tags and named entities.

## Architecture

EpiTator provides the following classes for organizing annotations.

AnnoDoc - The document being annotated. The AnnoDoc links to the tiers of annotations applied to it.

AnnoTier - A group of AnnoSpans. Each annotator creates one or more tiers of annotations.

AnnoSpan - A span of text with an annotation applied to it.

## License
Copyright 2016 EcoHealth Alliance

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
