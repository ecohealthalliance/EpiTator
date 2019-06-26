#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.infection_annotator import InfectionAnnotator
from epitator.incident_annotator import IncidentAnnotator
import datetime


def find(li, func):
    if len(li) > 0:
        if func(li[0]):
            return li[0]
        else:
            return find(li[1:], func)


class TestIncidentAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = IncidentAnnotator()

    def test_incident_1(self):
        doc = AnnoDoc(
            'It brings the number of cases reported to 28 in Jeddah since 27 March 2014',
            date=datetime.datetime(2018, 10, 2))
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
As of [Thu 7 Sep 2017], there have been at total of:
157 laboratory-confirmed cases of MERS-CoV infection, including
69 deaths [reported case fatality rate 40.2 percent],
103 recoveries, and 0 currently active cases/infections in Greece.
        """)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[0].metadata, {
                'value': 157,
                'type': 'cumulativeCaseCount',
                'status': 'confirmed',
                'resolvedDisease': {
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
                'value': 69,
                'type': 'cumulativeDeathCount',
                'species': {
                    'id': 'tsn:180092',
                    'label': 'Homo sapiens'
                },
                'resolvedDisease': {
                    'label': 'Middle East respiratory syndrome',
                    'id': 'https://www.wikidata.org/wiki/Q16654806'
                },
                'dateRange': [
                    datetime.datetime(2017, 9, 7, 0, 0),
                    datetime.datetime(2017, 9, 8, 0, 0)]
            })

    def test_disease_scope(self):
        doc = AnnoDoc("""
POLIOMYELITIS UPDATE:
*****************************************************************************

Poliovirus Weekly Update 26 Sep 2018, WHO
-----------------------------------------
New wild poliovirus cases reported this week: 0
Total number of wild poliovirus cases in 2018: 18
Total number of wild poliovirus cases in 2017: 22

New cVDPV cases reported this week: 10
Total number of cVDPV cases (all types) in 2018: 53
Total number of cVDPV cases (all types) in 2017: 96

Papua New Guinea
- 2 new cases of cVDPV1 were reported in the past week, bringing the total number of cases in 2018 to 14.
These latest reported cases are from Jiwaka and Eastern Highlands provinces and had onset of paralysis on [13 Aug 2018 and 16 Jun 2018], respectively.
- The polio teams are coordinating with the broader humanitarian emergency network as was done during the recent Ebola outbreak that infected 17 people.
- 5 deaths were reported in 2002.

Middle East
- No new cases of cVDPV2 were reported in the past week in Syria.
""")
        doc.add_tier(self.annotator)
        # 17 cases of Ebola
        self.assertEqual(
            doc.tiers['incidents'].spans[-2].metadata['resolvedDisease']['id'],
            'http://purl.obolibrary.org/obo/DOID_4325')
        # The final report of 5 deaths should be associated with polio
        self.assertEqual(
            doc.tiers['incidents'].spans[-1].metadata['resolvedDisease']['id'],
            'http://purl.obolibrary.org/obo/DOID_4953')

    def test_date_handling(self):
        doc = AnnoDoc("""
As of today, 30 Sep 2014, there have been 31 cases reported in Poland.
Yesterday 2 patients died.
""")
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['incidents'].spans[0].metadata['dateRange'],
            [datetime.datetime(2014, 9, 30, 0, 0), datetime.datetime(2014, 10, 1, 0, 0)])
        self.assertEqual(
            doc.tiers['incidents'].spans[1].metadata['dateRange'],
            [datetime.datetime(2014, 9, 29, 0, 0), datetime.datetime(2014, 9, 30, 0, 0)])

    def test_sentence_segmentation(self):
        doc = AnnoDoc("""
2 cases on 26 Dec 2014

1- Riyadh, Saudi Arabia: 31-year-old Saudi female, non-healthcare worker, currently in critical condition
2- Qurayyat, Saudi Arabia: 70-year-old Saudi male, non-healthcare worker, currently in stable condition



1 case on 19 Dec 2014

Alkharj: 53-year-old Saudi male, non-healthcare worker, history of animal exposure,
no history of contact with suspected or confirmed cases in the healthcare environment or in the community



2 cases on 25 Dec 2014

Alkharj: 53-year-old Saudi male, non-healthcare worker, history of pre-existing co-morbidities

Taif: 70-year-old Saudi female, non-healthcare worker, history of pre-existing co-morbidities



1 case on 22 Dec 2014

Taif: 29-year-old Expat female, healthcare worker, no history of co-morbidities
""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['incidents'].spans[0].metadata['locations']), 2)
        self.assertEqual(len(doc.tiers['incidents'].spans[-1].metadata['locations']), 1)

    def test_location_grouping(self):
        doc = AnnoDoc("""
In an update yesterday, officials reported 6 more cases,
which include 1 case in Paris, 1 case in London, and 4 cases in Australia,
which is in a security "red zone" area.
Today, the health ministry reported 3 more Ebola deaths.
""")
        doc.add_tier(self.annotator)
        self.assertEqual(
            len(find(doc.tiers['incidents'], lambda span: span.metadata['value'] == 6).metadata['locations']),
            3)
        self.assertEqual(
            len(find(doc.tiers['incidents'], lambda span: span.metadata['value'] == 1).metadata['locations']),
            1)
        self.assertEqual(
            len(find(doc.tiers['incidents'], lambda span: span.metadata['value'] == 3).metadata['locations']),
            3)

    def test_abiguous_date_count(self):
        doc = AnnoDoc("""
Dengue in West Virginia, United States:
Date / Cases / New cases per week

23 May 2018 / 106

29 Jun 2018 / 404 / 59

13 Jul 2018 / 540 / 68

9 Nov 2018 / 1774 / 49

16 Nov 2018 / 1859 / 85

23 Nov 2018 / 1907 / 48
""")
        doc.add_tier(self.annotator)
        self.assertTrue(1907 in [span.metadata['value'] for span in doc.tiers['incidents']])

    def test_non_cumulative_total(self):
        doc = AnnoDoc("""
Between 1 January 2011 - 22 Dec 2014, a total of 103 confirmed cases of hantavirus have been reported in Antarctica.
""")
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['incidents'][0].metadata['type'], 'caseCount')

    def test_global_cases(self):
        doc = AnnoDoc("""
As of June 2018 a total of 100 cases have been reported globally.
""")
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['incidents'][0].metadata['locations'][0]['name'], 'Earth')

    def test_species_association(self):
        doc = AnnoDoc('''
According to the OIE records, the annual numbers of reported glanders outbreaks (in equidae)
in India in 2017 was 106. For the months January to June 2018,
a total of 32 outbreaks have been reported to the OIE from India,
including 119 cases, of which 61 died and 58 had to be killed.

7 human cases of glanders occurred in June 1999.
''')
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[0].metadata, {
                'value': 119,
                'type': 'caseCount',
                'dateRange': [
                    datetime.datetime(2018, 6, 1, 0, 0),
                    datetime.datetime(2018, 7, 1, 0, 0)],
                'species': {'id': 'tsn:180691', 'label': 'Equus caballus'},
            })
        test_utils.assertHasProps(
            doc.tiers['incidents'].spans[-1].metadata, {
                'value': 7,
                'type': 'caseCount',
                'dateRange': [
                    datetime.datetime(1999, 6, 1, 0, 0),
                    datetime.datetime(1999, 7, 1, 0, 0)],
                'species': {'id': 'tsn:180092', 'label': 'Homo sapiens'},
            })
