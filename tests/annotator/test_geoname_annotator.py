#!/usr/bin/env python
# coding=utf8
"""Tests for the TokenAnnotator that annotates a sentence with tokens and their
offsets."""

import sys
import os
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.geoname_annotator import GeonameAnnotator
from annotator.loader import HealthMapFileLoader


class GeonameAnnotatorTest(unittest.TestCase):


    def test_chicago(self):

        annotator = GeonameAnnotator()

        text = 'I went to Chicago.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        self.assertEqual(len(doc.tiers['geonames'].spans), 1)
        self.assertEqual(doc.tiers['geonames'].spans[0].text, "Chicago")
        self.assertEqual(doc.tiers['geonames'].spans[0].label, "Chicago")
        self.assertEqual(doc.tiers['geonames'].spans[0].start, 10)
        self.assertEqual(doc.tiers['geonames'].spans[0].end, 17)

    def test_mulipart_names(self):

        annotator = GeonameAnnotator()

        text = 'I used to live in Seattle, WA'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        #print doc.tiers['geonames'].spans
        self.assertEqual(len(doc.tiers['geonames'].spans), 1)
        self.assertEqual(doc.tiers['geonames'].spans[0].text, "Seattle, WA")

    def test_mulipart_names2(self):

        annotator = GeonameAnnotator()

        text = 'I live in Taipei, Taiwan'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        self.assertEqual(len(doc.tiers['geonames'].spans), 1)
        self.assertEqual(doc.tiers['geonames'].spans[0].text, "Taipei, Taiwan")

    def test_mulipart_names3(self):

        annotator = GeonameAnnotator()

        text = 'England, France, Germany and Italy are countries in Eurpoe'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        self.assertEqual([
            span.text
            for span in doc.tiers['geonames'].spans
        ], [
            'England', 'France', 'Germany', 'Italy'
        ])

    def test_bug_causing_sentence(self):
        text = u"""
        In late June 2012, an increase in cases of prolonged fever for ≥3 days
        was reported from the Vanimo General Hospital in
        Vanimo, Sandaun Province.
        """
        annotator = GeonameAnnotator()
        doc = AnnoDoc(text)
        doc.add_tier(annotator)
        print doc.tiers['geonames'].spans

if __name__ == '__main__':
    unittest.main()