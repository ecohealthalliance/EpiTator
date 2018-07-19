#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from epitator.annotator import AnnoDoc
from epitator.structured_incident_annotator import StructuredIncidentAnnotator
import datetime
import logging


def with_log_level(logger, level):
    old_level = logger.level or logging.ERROR

    def decorator(fun):
        def logged_fun(*args, **kwargs):
            logger.setLevel(level)
            try:
                result = fun(*args, **kwargs)
                logger.setLevel(old_level)
                return result
            except:  # noqa: E722
                logger.setLevel(old_level)
                raise
        return logged_fun
    return decorator


def remove_empty_props(d):
    return {
        k: v
        for k, v in d.items()
        if v is not None
    }


class TestStructuredIncidentAnnotator(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.annotator = StructuredIncidentAnnotator()

    def test_count_table(self):
        doc = AnnoDoc('''
        Type / New / Confirmed / Probable / Suspect / Total

        Cases / 3 / 293 / / 32 / 413
        Deaths / 5 / 193 / 82 / 28 / 303
        ''')
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas, [{
            # Date/country??
            # Need to include because association rules are different for tables.
            'type': 'caseCount',
            'value': 3,
            'attributes': []
        }, {
            'type': 'cumulativeCaseCount',
            'value': 293,
            'attributes': ['confirmed']
        }, {
            'type': 'cumulativeCaseCount',
            'value': 32,
            'attributes': ['suspected']
        }, {
            'type': 'cumulativeCaseCount',
            'value': 413,
            'attributes': []
        }, {
            'type': 'deathCount',
            'value': 5,
            'attributes': []
        }, {
            'type': 'cumulativeDeathCount',
            'value': 193,
            'attributes': ['confirmed']
        }, {
            'type': 'cumulativeDeathCount',
            'value': 82,
            'attributes': []
        }, {
            'type': 'cumulativeDeathCount',
            'value': 28,
            'attributes': ['suspected']
        }, {
            'type': 'cumulativeDeathCount',
            'value': 303,
            'attributes': []
        }])

    def test_location_count_table(self):
        doc = AnnoDoc("""
Distribution of reported yellow fever cases from 1 Jul 2017-17 Apr 2018
Federal units / Reported / Discarded / Under investigation / Confirmed / Deaths
Acre (AC) / 1 / 1 / - / - / -
Alagoas (AL) / 8 / 2 / 6 / - / -
Amapá (AP) / 5 / 2 / 3 / - / -
Amazonas (AM) / 7 / 5 / 2 / - / -
Pará (PA) / 42 / 31 / 11 / - / -
Rondônia (RO) / 9 / 8 / 1 / - / -
Roraima (RR) / 3 / 3 / - / - / -
Tocantins (TO) / 17 / 15 / 2 / - / -
Bahia (BA) / 62 / 35 / 27 / - / -
Ceará (CE) / 4 / 3 / 1 / - / -
Maranhão (MA) / 7 / 5 / 2 / - / -
Paraíba (PB) / 5 / - / 5 / - / -
Pernambuco (PE) / 6 / 4 / 2 / - / -
Piauí (PI) / 9 / 6 / 3 / - / -
Rio Grande do Norte (RN) / 3 / 2 / 1 / - / -
Sergipe (SE) / 2 / 2 / - / - / -
Distrito Federal (DF) / 74 / 43 / 30 / 1 / 1
Goiás (GO) / 66 / 37 / 29 / - / -
Mato Grosso (MT) / 10 / 8 / 2 / - / -
Mato Grosso do Sul (MS) / 13 / 10 / 3 / - / -
Espírito Santo (ES) / 119 / 88 / 25 / 6 / 1
Minas Gerais (MG) / 1444 / 656 / 294 / 494 / 156
Rio de Janeiro (RJ) / 453 / 172 / 84 / 197 / 64
São Paulo (SP) / 2558 / 1655 / 444 / 459 / 120
Paraná (PR) / 110 / 102 / 8 / - / -
Rio Grande do Sul (RS) / 49 / 34 / 15 / - / -
Santa Catarina (SC) / 45 / 22 / 23 / - / -
Total / 5131 / 2951 / 1023 / 1157 / 342
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[1]['value'], 8)
        self.assertEqual(metadatas[1]['type'], 'caseCount')
        self.assertEqual(metadatas[1]['location']['geonameid'], '3408096')
        self.assertEqual(
            metadatas[1]['dateRange'],
            [datetime.datetime(2017, 7, 1),
             datetime.datetime(2018, 4, 18)])

    def test_date_count_table(self):
        doc = AnnoDoc("""
Cumulative case data
Report date / Cases / Deaths / New cases per week
26 Jun 2017 / 190 / 10 /
8 Sep 2017 / 300 / 12 /
9 Sep 2017 / 309 / 13 /
15 Sep 2017 / 319 / 14 /
6 Oct 2017 / 376 / 14 /
13 Oct 2017 /
20 Oct 2017 / 431 / 17 / 34
27 Oct 2017 / 457 / 18 / 26
3 Nov 2017 / 486 / 19 / 29""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[-1], {
            'value': 29,
            'type': 'caseCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 10, 28),
                datetime.datetime(2017, 11, 4)]
        })
        self.assertEqual(metadatas[-2], {
            'value': 19,
            'type': 'cumulativeDeathCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 11, 3),
                datetime.datetime(2017, 11, 4)]
        })

    def test_date_count_table_2(self):
        doc = AnnoDoc("""
| Report date | Cases |
| 6 Oct 2017  | 26    |
| 13 Oct 2017 | 29    |
| 20 Oct 2017 | 34    |""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas, [{
            'value': 26,
            'type': 'caseCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 9, 30),
                datetime.datetime(2017, 10, 7)]
        }, {
            'value': 29,
            'type': 'caseCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 10, 7),
                datetime.datetime(2017, 10, 14)]
        }, {
            'value': 34,
            'type': 'caseCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 10, 14),
                datetime.datetime(2017, 10, 21)]
        }])

    def test_non_incident_counts_and_species(self):
        doc = AnnoDoc("""
Species / Morbidity / Mortality / Susceptible / Cases / Deaths / Killed and disposed of / Slaughtered
Orange Spotted Snakehead (_Channa aurantimaculata_) / 100% / 1% / 32 / 30 / 1 / 28 / 3
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas, [{
            'attributes': [],
            'type': 'caseCount',
            'value': 30,
            'species': {
                'id': 'tsn:642745',
                'label': 'Channa aurantimaculata'}
        }, {
            'attributes': [],
            'type': 'deathCount',
            'value': 1,
            'species': {
                'id': 'tsn:642745',
                'label': 'Channa aurantimaculata'}
        }])

    def test_unknown_species_and_space_delimited_counts(self):
        doc = AnnoDoc("""
The epidemiological statistics accumulated since the start of the event are included in the following "outbreak summary":

Species / Susceptible / Cases / Deaths / Killed and disposed of / Slaughtered

Birds / 6 368 632 / 1 303 173 / 1 297 617 / 3 850 608 / 0

Black-crowned night-heron / not available / 1 / 1 / 0 / 0

Passeridae (unidentified) / not available / 2 / 2 / 0 / 0

Pale thrush / not available / 1 / 1 / 0 / 0
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[0], {
            'attributes': [],
            'type': 'caseCount',
            'value': 1303173,
            'species': {'id': 'tsn:174371', 'label': 'Aves'}
        })
        self.assertEqual(metadatas[-1], {
            'attributes': [],
            'type': 'deathCount',
            'value': 1,
            'species': "Cannot parse"
        })

    # @with_log_level(logging.getLogger('epitator.structured_incident_annotator'), logging.INFO)
    def test_multi_section_table(self):
        doc = AnnoDoc("""
Disease update
--------------
Confirmed, probable, and suspect cases and deaths from Ebola virus disease in Guinea, Liberia, and Sierra Leone, as of 30 Jun 2014
Type / New* / Confirmed / Probable / Suspect / Totals by country
Guinea
Cases / 3 / 293 / 88 / 32 / 413
Deaths / 5 / 193 / 82 / 28 / 303

Liberia
Cases / 8 / 52 / 21 / 34 / 107
Deaths / 7 / 33 / 17 / 15 / 65

Sierra Leone
Cases / 11 / 199 / 31 / 9 / 239
Deaths / 2 / 65 / 29 / 5 / 99

Totals
Cases / 22 / 544 / 140 / 75 / 759
Deaths / 14 / 291 / 128 / 48 / 467
*New cases were reported between 25-29 Jun 2014
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[4]['type'], 'cumulativeCaseCount')
        self.assertEqual(metadatas[4]['dateRange'], [
            datetime.datetime(2014, 6, 30, 0, 0),
            datetime.datetime(2014, 7, 1, 0, 0)])
        self.assertEqual(metadatas[4]['value'], 413)
        self.assertEqual(metadatas[4]['location']['geonameid'], '2420477')

    def test_number_in_header(self):
        doc = AnnoDoc("""
Health Jurisdiction / Cases (percentage) / Incidence rate per 100 000 Person-Years
Salt Lake county / 162 (68.9) / 14.4
Utah county / 45 (19.1) / 7.6
Bear River / 5 (2.1) / 2.8
Southeast Utah / 2 (0.9) / 5.0
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[0]['type'], 'caseCount')
        self.assertEqual(metadatas[0]['value'], 162)
        self.assertEqual(metadatas[0]['location']['geonameid'], '5781004')

    def test_unusual_format(self):
        doc = AnnoDoc("""
For subscribers' convenience, we hereby reproduce Israel's annual rabies statistics since 2014:

Year // badger / cat / fox / jackal / wolf / dog / cattle / sheep / horse // total
2014 // 3 / 0 / 2 / 2 / 4 / 2 / 1 / 0 / 0 // 14
2015 // 12 / 1 / 1 / 3 / 0 / 1 / 7 / 0 / 1 // 20
2016 // 12 / 0 / 7 / 5 / 0 / 0 / 5 / 0 / 1 // 30
2017 // 10 / 2 / 0 / 47 / 0 / 0 / 14 / 1 / 0 // 74
2018 // 4 / 0 / 0 / 35 / 0 / 1 / 7 / 1 / 1 // 51
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[0]['type'], 'caseCount')
        self.assertEqual(metadatas[0]['value'], 3)
        self.assertEqual(metadatas[0]['species']['label'], 'Taxidea taxus')
        self.assertEqual(metadatas[0]['dateRange'], [
            datetime.datetime(2014, 1, 1, 0, 0),
            datetime.datetime(2015, 1, 1, 0, 0)])

    def test_date_association(self):
        doc = AnnoDoc("""
The outbreak strains of salmonella have infected a reported 961 people in 48 states [only Alaska and Delaware have not reported cases - Mod.LL] and the District of Columbia. Illnesses started on dates ranging from 4 January 2017 to 31 July 2017.
State / Number of Cases
Alabama / 25
Arizona / 6
Arkansas / 9
California / 54
Virginia / 56
Washington / 22
West Virginia / 17
Wisconsin / 24
Wyoming / 10""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents']
        ]
        self.assertEqual(metadatas[0]['dateRange'], [
            datetime.datetime(2017, 1, 4, 0, 0),
            datetime.datetime(2017, 8, 1, 0, 0)])

    def test_fp_table_merging(self):
        doc = AnnoDoc("""
Non-Latin Caribbean

Bahamas / week 30 [ending 25 Jul 2014] / 0 / 0 / 6 / 0

Dominica / week 28 [ending 11 Jul 2014] / 3559 / 141 / 0 / 0

Jamaica / week 29 [ending 18 Jul 2014] / 0 / 0 / 1 / 0

Turks & Caicos Islands / week 28 [ending 11 Jul 2014] / 0 / 10 / 7 / 0

US Virgin Islands / week 29 [ending 18 Jul 2014] / 0 / 2 / 7 / 0


Andean area:

Bolivia / 9 / 0 / 0 / 3 / 0

Colombia / 30 / 0 / 0 / 1 / 0

Peru / 28 / 0 / 0 / 3 / 0
""")
        doc.add_tier(self.annotator)
