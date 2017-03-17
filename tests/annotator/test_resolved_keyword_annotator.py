#!/usr/bin/env python
import sys
import os
import unittest
import test_utils

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.resolved_keyword_annotator import ResolvedKeywordAnnotator

class ResolvedKeywordAnnotatorTest(unittest.TestCase):
    def setUp(self):
        self.annotator = ResolvedKeywordAnnotator()
    def test_contained_name_resolution(self):
        doc = AnnoDoc("hepatitis B is also referred to as hepatitis B infection")
        doc.add_tier(self.annotator)
        expected_spans = [
            dict(textOffsets=[[0,11]],
                uris=["http://purl.obolibrary.org/obo/DOID_2043"]),
            dict(textOffsets=[[35,56]],
                uris=["http://purl.obolibrary.org/obo/DOID_2043"])]
        spans = doc.tiers['resolved_keywords'].spans
        self.assertEqual(len(spans), len(expected_spans))
        for span, expected_span in zip(spans, expected_spans):
            test_utils.assertHasProps(span.to_dict(), expected_span)
    def test_capitalization_variations(self):
        doc = AnnoDoc("Mumps is mumps")
        doc.add_tier(self.annotator)
        expected_uris = [
            'http://purl.obolibrary.org/obo/DOID_10264',
            'http://purl.obolibrary.org/obo/DOID_10264']
        for span, expected_uri in zip(doc.tiers['resolved_keywords'].spans, expected_uris):
            self.assertEqual(span.resolutions[0]['uri'], expected_uri)
    def test_acroynms(self):
        doc = AnnoDoc("Ebola Virus disease is EVD")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['resolved_keywords'].spans[-1].to_dict(), dict(
                dict(textOffsets=[[23,26]],
                uris=["http://purl.obolibrary.org/obo/DOID_4325"])))
        doc = AnnoDoc('AIDS as in the disease, not as in "he aids his boss"')
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['resolved_keywords'].spans[-1].to_dict(), dict(
                dict(textOffsets=[[0,4]],
                uris=["http://purl.obolibrary.org/obo/DOID_635"])))

if __name__ == '__main__':
    unittest.main()
