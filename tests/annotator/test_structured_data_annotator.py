#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from epitator.annotator import AnnoDoc
from epitator.structured_data_annotator import StructuredDataAnnotator


def stringify_data_annospans(structured_data):
    if structured_data['type'] == 'table':
        structured_data['data'] = [
            [value.text for value in row]
            for row in structured_data['data']]
    else:
        structured_data['data'] = {
            key.text: value.text
            for key, value in structured_data['data'].items()}
    return structured_data


class TestStructuredDataAnnotator(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.annotator = StructuredDataAnnotator()

    def test_no_structed_data(self):
        doc = AnnoDoc('''
Date: 11/20/2017

The government said that a suspected bird flu case was confirmed to be highly pathogenic and
imposed a travel ban to prevent further spread of the animal virus.

A map can be accessed at: http://example.com
''')
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['structured_data'].spans, [])

    def test_count_table(self):
        doc = AnnoDoc('''
        Cases / 22 / 544 / / 75 / 759
        Deaths / 14 / 291 / 128 / 48 / 467

        *New cases were reported between 25-29 Jun 2014
        ''')
        doc.add_tier(self.annotator)
        metadatas = [
            stringify_data_annospans(span.metadata)
            for span in doc.tiers['structured_data'].spans
        ]
        self.assertEqual(metadatas[0], {
            'data': [
                ['Cases', '22', '544', '', '75', '759'],
                ['Deaths', '14', '291', '128', '48', '467']
            ],
            'type': 'table'
        })

    def test_count_table_2(self):
        doc = AnnoDoc('''
Outbreak 2: Taraz City, Dzhambul
Date of start of the outbreak: 10 Oct 2017
Outbreak status: resolved on 15 Nov 2017
Epidemiological unit: other
Affected animals: species / susceptible / cases / deaths / killed and disposed of / slaughtered
Dogs / 20 /1 / 1 / 0 / 0

Summary of outbreaks
Total outbreaks: 2
Total animals affected:
species / susceptible / cases / deaths / killed and disposed of / slaughtered
Cattle / 6 / 0 / 0 / 0 / 0
Dogs / 22 / 2 / 1 / 0 / 0
Equidae / 6 / 0 / 0 / 0 / 0
Sheep/goats / 15 / 0 / 0 / 0 / 0
''')
        doc.add_tier(self.annotator)
        metadatas = [
            stringify_data_annospans(span.metadata)
            for span in doc.tiers['structured_data'].spans
        ]
        self.assertEqual(metadatas[0], {
            'data': {
                'Date of start of the outbreak': '10 Oct 2017',
                'Epidemiological unit': 'other',
                'Outbreak 2': 'Taraz City, Dzhambul',
                'Outbreak status': 'resolved on 15 Nov 2017'
            },
            'type': 'keyValuePairs'
        })
        self.assertEqual(metadatas[1], {
            'type': 'table',
            'data': [
                ['Affected animals: species', 'susceptible', 'cases', 'deaths', 'killed and disposed of', 'slaughtered'],
                ['Dogs', '20', '1', '1', '0', '0']
            ],
            'type': 'table'
        })
        self.assertEqual(metadatas[2], {
            'type': 'table',
            'data': [
                ['species', 'susceptible', 'cases', 'deaths', 'killed and disposed of', 'slaughtered'],
                ['Cattle', '6', '0', '0', '0', '0'],
                ['Dogs', '22', '2', '1', '0', '0'],
                ['Equidae', '6', '0', '0', '0', '0'],
                ['Sheep', 'goats', '15', '0', '0', '0', '0']
            ],
            'type': 'table'
        })

    def test_count_list(self):
        doc = AnnoDoc('''
The 15 non-fatal cases confirmed across the state since the year began are as follows:

ArithmeticError County - 1 case

TypeError County - 1 case

Python County - 2 cases

Java County - 2 cases

Scala County - 1 case

Scheme County - 1 case

Meteor County - 1 case

Boolean County - 1 case (not including the fatality)

Integer County - 3 cases
''')
        doc.add_tier(self.annotator)
        metadatas = [
            stringify_data_annospans(span.metadata)
            for span in doc.tiers['structured_data'].spans
        ]
        self.assertEqual(metadatas[0], {
            'type': 'keyValuePairs',
            'data': {
                'ArithmeticError County': '1 case',
                'TypeError County': '1 case',
                'Python County': '2 cases',
                'Java County': '2 cases',
                'Scala County': '1 case',
                'Scheme County': '1 case',
                'Meteor County': '1 case',
                'Boolean County': '1 case (not including the fatality)',
                'Integer County': '3 cases'
            }
        })
