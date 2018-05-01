#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from epitator.annotator import AnnoDoc
from epitator.structured_incident_annotator import StructuredIncidentAnnotator
import datetime


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

        Cases / 3 / 293 / 88 / 32 / 413
        Deaths / 5 / 193 / 82 / 28 / 303
        ''')
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents'].spans
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
            'value': 88,
            'attributes': []
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
            for span in doc.tiers['structured_incidents'].spans
        ]
        self.assertEqual(metadatas[2]['value'], 8)
        self.assertEqual(metadatas[2]['type'], 'caseCount')
        self.assertEqual(metadatas[2]['location']['geonameid'], '3408096')
        self.assertEqual(
            metadatas[2]['dateRange'],
            [datetime.datetime(2017, 7, 1),
             datetime.datetime(2018, 4, 18)])

    def test_date_count_table(self):
        doc = AnnoDoc("""
Cumulative case data
Report date / Cases / Deaths / New cases per week
26 Jun 2017 / 190 / 10 /
15 Sep 2017 / 319 / 14 /
6 Oct 2017 / 376 / 14 /
13 Oct 2017 / 397 / 15 / 21
20 Oct 2017 / 431 / 17 / 34
27 Oct 2017 / 457 / 18 / 26
3 Nov 2017 / 486 / 19 / 29
""")
        doc.add_tier(self.annotator)
        metadatas = [
            remove_empty_props(span.metadata)
            for span in doc.tiers['structured_incidents'].spans
        ]
        self.assertEqual(metadatas[-1], {
            'value': 19,
            'type': 'deathCount',
            'attributes': [],
            'dateRange': [
                datetime.datetime(2017, 11, 3),
                datetime.datetime(2017, 11, 4)]
        })
