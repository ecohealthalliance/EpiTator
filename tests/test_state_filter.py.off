#!/usr/bin/env python
"""Tests for the state-based filters on the GeonameAnnotator"""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.geoname_annotator import GeonameAnnotator


class StateFilterTest(unittest.TestCase):

    def setUp(self):
        self.doc = AnnoDoc()
        self.annotator = GeonameAnnotator()

    def test_simple_sentence(self):

        self.doc.text = "I'm from Fairview, Oregon and also Duluth, Minnesota."
        self.doc.add_tier(self.annotator)

        print self.doc.tiers['geonames']

        self.assertEqual(len(self.doc.tiers['geonames'].spans), 4)


if __name__ == '__main__':
    unittest.main()