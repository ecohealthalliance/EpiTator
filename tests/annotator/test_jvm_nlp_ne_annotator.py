#!/usr/bin/env python
"""Tests for the JVMNLPAnnotator that annotates a sentence with data from a
webservice providing Stanford NLP results.

As these tests require the presence of a well-running webservice, they may be
considered more of an integration test than a unit test.

The code for the webservice required is github.com/ecohealthalliance/jvm-nlp
"""
import unittest
from epitator.annotator import AnnoDoc
from epitator.jvm_nlp_annotator import JVMNLPAnnotator


class JVMNLPAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = JVMNLPAnnotator(['nes'])

    def test_no_nes(self):
        text = 'I went to see her in a boat.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)
        nes = doc.tiers['stanford.nes'].spans
        self.assertEqual(len(nes), 0)

    def test_simple_ne(self):
        text = 'I went to Chicago.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        nes = doc.tiers['stanford.nes'].spans
        self.assertEqual(nes[0].type, 'LOCATION')
        self.assertEqual(nes[0].text, 'Chicago')
        self.assertEqual(nes[0].start, 10)
        self.assertEqual(nes[0].end, 17)

    def test_multiple_word_ne(self):

        doc = AnnoDoc("Winston Smith works at the Ministry of Truth.")
        doc.add_tier(self.annotator)

        nes = doc.tiers['stanford.nes'].spans
        self.assertEqual(nes[1].type, 'ORGANIZATION')
        self.assertEqual(nes[1].start, 27)
        self.assertEqual(nes[1].end, 44)
        self.assertEqual(nes[1].label, 'Ministry of Truth')

    def test_bol_eol_nes(self):

        doc = AnnoDoc("Oceania has always been at war with Eastasia.")
        doc.add_tier(self.annotator)

        nes = doc.tiers['stanford.nes'].spans

        self.assertEqual(nes[0].start, 0)
        self.assertEqual(nes[0].end, 7)
        self.assertEqual(nes[0].type, 'LOCATION')
        self.assertEqual(nes[0].label, 'Oceania')

        self.assertEqual(nes[1].start, 36)
        self.assertEqual(nes[1].end, 44)
        self.assertEqual(nes[1].type, 'LOCATION')
        self.assertEqual(nes[1].label, 'Eastasia')


if __name__ == '__main__':
    unittest.main()
