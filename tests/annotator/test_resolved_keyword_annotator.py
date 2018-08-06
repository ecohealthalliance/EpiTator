#!/usr/bin/env python
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.resolved_keyword_annotator import ResolvedKeywordAnnotator
from six.moves import zip
import logging
logging.getLogger('epitator.resolved_keyword_annotator').setLevel(logging.ERROR)


class ResolvedKeywordAnnotatorTest(unittest.TestCase):
    def setUp(self):
        self.annotator = ResolvedKeywordAnnotator()

    def test_contained_name_resolution(self):
        doc = AnnoDoc(
            "hepatitis B is also referred to as hepatitis B infection")
        doc.add_tier(self.annotator)
        expected_spans = [
            dict(textOffsets=[0, 11],
                 uris=['http://purl.obolibrary.org/obo/DOID_2043']),
            dict(textOffsets=[35, 56],
                 uris=['http://purl.obolibrary.org/obo/DOID_2043'])]
        spans = doc.tiers['resolved_keywords'].spans
        self.assertEqual(len(spans), len(expected_spans))
        for span, expected_span in zip(spans, expected_spans):
            self.assertEqual([r['entity_id'] for r in span.resolutions],
                             expected_span['uris'])
            self.assertEqual([span.start, span.end],
                             expected_span['textOffsets'])

    def test_capitalization_variations(self):
        doc = AnnoDoc("Mumps is mumps")
        doc.add_tier(self.annotator)
        expected_uris = [
            'http://purl.obolibrary.org/obo/DOID_10264',
            'http://purl.obolibrary.org/obo/DOID_10264']
        for span, expected_uri in zip(doc.tiers['resolved_keywords'].spans,
                                      expected_uris):
            self.assertEqual(span.resolutions[0]['entity_id'], expected_uri)

    def test_MERS(self):
        doc = AnnoDoc('There have been 6 new cases of MERS since last week.')
        doc.add_tier(self.annotator)
        first_span = doc.tiers['resolved_keywords'].spans[0]
        self.assertEqual(first_span.resolutions[0]['entity_id'],
                         'https://www.wikidata.org/wiki/Q16654806')

    def test_acroynms(self):
        doc = AnnoDoc("Ebola Virus disease is EVD")
        doc.add_tier(self.annotator)
        resolved_keyword = doc.tiers['resolved_keywords'].spans[-1].to_dict()
        test_utils.assertHasProps(
            resolved_keyword, {'textOffsets': [[23, 26]]})
        test_utils.assertHasProps(resolved_keyword['resolutions'][0], {
            'entity_id': 'http://purl.obolibrary.org/obo/DOID_4325'
        })
        doc = AnnoDoc('AIDS as in the disease, not as in "he aids his boss"')
        doc.add_tier(self.annotator)
        resolved_keyword = doc.tiers['resolved_keywords'].spans[-1].to_dict()
        test_utils.assertHasProps(
            resolved_keyword, dict(
                textOffsets=[[0, 4]]))
        test_utils.assertHasProps(
            resolved_keyword['resolutions'][0]['entity'],
            {'id': 'http://purl.obolibrary.org/obo/DOID_635'})

    def test_very_long_article(self):
        import os
        path = os.path.dirname(__file__) + "/resources/WhereToItaly.txt"
        with open(path, encoding='utf-8') as file:
            doc = AnnoDoc(file.read())
            doc.add_tier(self.annotator)

    def test_species(self):
        doc = AnnoDoc("His illness was caused by cattle")
        doc.add_tier(self.annotator)
        resolved_keyword = doc.tiers['resolved_keywords'].spans[-1].to_dict()
        test_utils.assertHasProps(resolved_keyword['resolutions'][0], {
            'entity_id': 'tsn:180704',
            'entity': {
                'type': 'species',
                'id': 'tsn:180704',
                'label': 'Bovidae'}
        })
