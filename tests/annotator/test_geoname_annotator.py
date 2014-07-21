#!/usr/bin/env python
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


if __name__ == '__main__':
    unittest.main()