# Annie the annotator

Annotators for extracting epidemiologic information from text.

## Architecture

Annie provides the following classes for dealing with annotations.

AnnoDoc - The document being annotated. The AnnoDoc links to the tiers of annotations applied to it.

AnnoTier - A group of AnnoSpans. Generally each annotator creates a new tier of annotations.

AnnoSpan - A span of text with an annotation applied to it.

## Annotators

### Geoname Annotator

The geoname annotator uses the geonames.org dataset to resolve mentions of geonames.
A classifier is used to disambiguate geonames and rule out false positives.

To use the geoname annotator run the following command to import geonames.org data into an embedded sqlite3 database:

```
python -m annotator.sqlite_import_geonames
```

### Resolved Keyword Annotator

The resolved keyword annotator uses synonyms from the disease ontology to 
resolve mentions of diseases to doid uris.

To use the geoname annotator run the following command to import the disease ontology
data into an embedded sqlite3 database:

```
python -m annotator.sqlite_import_disease_ontology
```

### Count Annotator

The count annotator identifies counts, and case counts in particular.
The count's value is extracted and parsed. Attributes such as whether the count
refers to cases or deaths, or whether the value is approximate, are also extracted.

### JVM-NLP Annotator

The jvm_nl_annotator relies on a server from this project to create annotations using Stanford's NLP library:

https://github.com/ecohealthalliance/jvm-nlp

The AnnoTiers it creates include tokens, sentences, pos tags and named entities.

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
