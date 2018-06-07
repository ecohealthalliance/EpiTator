EpiTator
********

Annotators for extracting epidemiological information from text.

Installation
============

.. code:: bash

    pip install epitator
    python -m spacy download en_core_web_sm


Annotators
==========

Geoname Annotator
-----------------

The geoname annotator uses the geonames.org dataset to resolve mentions of geonames.
A classifier is used to disambiguate geonames and rule out false positives.

To use the geoname annotator run the following command to import geonames.org
data into epitator's embedded sqlite3 database:

You should review the geonames license before using this data.

.. code:: bash

    python -m epitator.importers.import_geonames


Usage
-----

.. code:: python

    from epitator.annotator import AnnoDoc
    from epitator.geoname_annotator import GeonameAnnotator
    doc = AnnoDoc("Where is Chiang Mai?")
    doc.add_tiers(GeonameAnnotator())
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


Resolved Keyword Annotator
--------------------------

The resolved keyword annotator uses an sqlite database of entities to resolve
mentions of multiple synonyms for an entity to a single id.
This project includes scripts for importing diseases and animal species into
that database. The following commands cab be used to invoke them:

The scripts import data from the `Disease Ontology <http://disease-ontology.org/>`_,
`Wikidata <https://www.wikidata.org/>`_
and `ITIS <https://www.itis.gov/>`_.
You should review their licenses and terms of use before using this data.
Currently the Disease Ontology is under public domain and ITIS requests citation.

.. code:: bash

    python -m epitator.importers.import_species
    python -m epitator.importers.import_disease_ontology
    python -m epitator.importers.import_wikidata


Usage
-----

.. code:: python

    from epitator.annotator import AnnoDoc
    from epitator.resolved_keyword_annotator import ResolvedKeywordAnnotator
    doc = AnnoDoc("5 cases of smallpox")
    doc.add_tiers(ResolvedKeywordAnnotator())
    annotations = doc.tiers["resolved_keywords"].spans
    annotations[0].metadata["resolutions"]
    # = [{'entity': <sqlite3.Row>, 'entity_id': u'http://purl.obolibrary.org/obo/DOID_8736', 'weight': 3}]


Count Annotator
---------------

The count annotator identifies counts, and case counts in particular.
The count's value is extracted and parsed. Attributes such as whether the count
refers to cases or deaths, or whether the value is approximate are also extracted.

Usage
-----

.. code:: python

    from epitator.annotator import AnnoDoc
    from epitator.count_annotator import CountAnnotator
    doc = AnnoDoc("5 cases of smallpox")
    doc.add_tiers(CountAnnotator())
    annotations = doc.tiers["counts"].spans
    annotations[0].metadata
    # = {'count': 5, 'text': '5 cases', 'attributes': ['case']}


Date Annotator
--------------

The date annotator identifies and parses dates and date ranges.
All dates are parsed into datetime ranges. For instance, a date like "11-6-87"
would be parsed as a range from the start of the day to the start of the next day,
while a month like "December 2011" would be parsed as a range from the start
of December 1st to the start of the next month.

Usage
-----

.. code:: python

    from epitator.annotator import AnnoDoc
    from epitator.date_annotator import DateAnnotator
    doc = AnnoDoc("From March 5 until April 7 1988")
    doc.add_tiers(DateAnnotator())
    annotations = doc.tiers["dates"].spans
    annotations[0].metadata["datetime_range"]
    # = [datetime.datetime(1988, 3, 5, 0, 0), datetime.datetime(1988, 4, 7, 0, 0)]


Structured Data Annotator
-------------------------

The structured data annotator identifies and parses embedded tables.

Usage
-----

.. code:: python

    from epitator.annotator import AnnoDoc
    from epitator.structured_data_annotator import StructuredDataAnnotator
    doc = AnnoDoc("""
    species | cases | deaths
    Cattle  | 0     | 0
    Dogs    | 2     | 1
    """)
    doc.add_tiers(StructuredDataAnnotator())
    annotations = doc.tiers["structured_data"].spans
    annotations[0].metadata
    # = {'data': [
    #       [AnnoSpan(1-8, species), AnnoSpan(11-16, cases), AnnoSpan(19-25, deaths)],
    #       [AnnoSpan(26-32, Cattle), AnnoSpan(36-37, 0), AnnoSpan(44-45, 0)],
    #       [AnnoSpan(46-50, Dogs), AnnoSpan(56-57, 2), AnnoSpan(64-65, 1)]],
    #    'type': 'table'}


Architecture
============

EpiTator provides the following classes for organizing annotations.

AnnoDoc - The document being annotated. The AnnoDoc links to the tiers of annotations applied to it.

AnnoTier - A group of AnnoSpans. Each annotator creates one or more tiers of annotations.

AnnoSpan - A span of text with an annotation applied to it.

License
=======

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
