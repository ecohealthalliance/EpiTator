#!/usr/bin/env python
"""Tests for the HealthMapFileLoader"""

import sys
import os
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.loader import HealthMapFileLoader


class HealthMapFileLoaderTest(unittest.TestCase):

    def setUp(self):

        self.loader = HealthMapFileLoader()

    def test_rabies_doc(self):

        filename = os.path.join(os.path.dirname(__file__), 'resources/rabies.md')

        doc = self.loader.load(filename)

        self.assertEqual(doc.text,
            """\n    A mountain lion that surprised four campers and attacked a dog """ +\
             """last week in the Tonto National Forest has been confirmed positive for rabies.\n            """)

        self.assertEqual(doc.properties['_id'], '532ca4a5f99fe75cf5384bdf')
        self.assertEqual(doc.properties['description'],
            'Mountain lion which attacked four campers confirmed positive for rabies - Examiner.com')
        self.assertEqual(doc.properties['meta']['country'], 'United States')

        self.assertEqual(len(doc.tiers['html'].spans), 0)


if __name__ == '__main__':
    unittest.main()