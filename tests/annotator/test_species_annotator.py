#!/usr/bin/env python
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.species_annotator import SpeciesAnnotator


class SpeciesAnnotatorTest(unittest.TestCase):
    def setUp(self):
        self.annotator = SpeciesAnnotator()

    def test_species(self):
        doc = AnnoDoc("His illness was caused by cattle")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(doc.tiers['species'].spans[-1].metadata, {
            'species': {
                'id': 'tsn:180704',
                'label': 'Bovidae'}
        })

    def test_species_false_positive(self):
        # Sierra wil be detected as a species if using naive ontology keyword
        # matching.
        doc = AnnoDoc("""
Guinea, 3 new cases and 5 deaths; Liberia, 8 new cases with 7 deaths;
and Sierra Leone 11 new cases and 2 deaths.""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['species']), 0)

    def test_species_humans(self):
        doc = AnnoDoc("""
5 humans were infected - 4 men and 1 woman. One infected person was admitted to the hospital.""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['species']), 4)
        self.assertTrue(all(s.metadata['species']['id'] == 'tsn:180092'
                            for s in doc.tiers['species']))
