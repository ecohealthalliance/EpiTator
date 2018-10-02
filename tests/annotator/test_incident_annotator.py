#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.infection_annotator import InfectionAnnotator
from epitator.incident_annotator import IncidentAnnotator
import datetime

class TestIncidentAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = IncidentAnnotator()

    def test_incident_1(self):
        doc = AnnoDoc(
            'It brings the number of cases reported to 28 in Jeddah since 27 March 2014',
            date=datetime.datetime(2018,10,2))
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[0].metadata, {
                'value': 28,
                'type': 'caseCount',
                'dateRange': [
                    datetime.datetime(2014, 3, 27, 0, 0),
                    datetime.datetime(2018, 10, 2, 0, 0)]
            })

    def test_incident_2(self):
        doc = AnnoDoc('There were 2 new cases in California in 2012.')
        case_counts = doc.require_tiers('infections', via=InfectionAnnotator)
        attribute_remappings = {
            'infection': 'case'
        }
        for span in case_counts:
            span.metadata['attributes'] = [
                attribute_remappings.get(attribute, attribute)
                for attribute in span.metadata['attributes']]
        doc.add_tier(self.annotator, case_counts=case_counts)
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[0].metadata, {
                'value': 2,
                'type': 'caseCount',
                'dateRange': [
                    datetime.datetime(2012, 1, 1, 0, 0),
                    datetime.datetime(2013, 1, 1, 0, 0)]
            })

    def test_incident_3(self):
        doc = AnnoDoc("""
As of [Thu 7 Sep 2017], there have been a total of:
1715 laboratory-confirmed cases of MERS-CoV infection, including
690 deaths [reported case fatality rate 40.2 percent],
1003 recoveries, and 0 currently active cases/infections in Greece.
        """)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[0].metadata, {
                'value': 1715,
                'type': 'cumulativeCaseCount',
                'status': 'confirmed',
                'resolvedDisease': {
                    'type': 'disease',
                    'label': 'Middle East respiratory syndrome',
                    'id': 'https://www.wikidata.org/wiki/Q16654806'
                },
                'dateRange': [
                    datetime.datetime(2017, 9, 7, 0, 0),
                    datetime.datetime(2017, 9, 8, 0, 0)]
            })
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[1].metadata['locations'][0], {
                'latitude': 39.0,
                'name': 'Hellenic Republic',
                'id': '390903',
                'countryCode': 'GR',
                'asciiname': 'Hellenic Republic',
                'countryName': 'Hellenic Republic',
                'featureCode': 'PCLI',
                'namesUsed': 'Greece',
                'admin1Code': '00',
                'longitude': 22.0
            })
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[1].metadata, {
                'value': 690,
                'type': 'cumulativeDeathCount',
                'species': {'id': 'tsn:180092', 'label': 'Homo sapiens'},
                'resolvedDisease': {
                    'type': 'disease',
                    'label': 'Middle East respiratory syndrome',
                    'id': 'https://www.wikidata.org/wiki/Q16654806'
                },
                'dateRange': [
                    datetime.datetime(2017, 9, 7, 0, 0),
                    datetime.datetime(2017, 9, 8, 0, 0)]
            })
