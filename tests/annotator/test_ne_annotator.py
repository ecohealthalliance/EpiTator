#!/usr/bin/env python
"""Tests for the NEAnnotator that annotates a sentence with named entities."""
import unittest
from epitator.annotator import AnnoDoc
from epitator.ne_annotator import NEAnnotator


class NEAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = NEAnnotator()

    def test_simple_sentence(self):

        self.doc = AnnoDoc("I'm married to Joe.")
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['nes'].spans), 1)

        self.assertEqual(self.doc.tiers['nes'].spans[0].label, 'PERSON')
        self.assertEqual(self.doc.tiers['nes'].spans[0].start, 15)
        self.assertEqual(self.doc.tiers['nes'].spans[0].end, 18)

    def test_complex_text(self):

        self.doc = AnnoDoc(
            "I'm married to Joe from New York City. "
            "That is in the United States who works for the Raytheon Corporation."
        )
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['nes'].spans), 4)

        self.assertEqual(self.doc.tiers['nes'].spans[0].label, 'PERSON')
        self.assertEqual(self.doc.tiers['nes'].spans[0].text, 'Joe')
        self.assertEqual(self.doc.tiers['nes'].spans[0].start, 15)
        self.assertEqual(self.doc.tiers['nes'].spans[0].end, 18)

        self.assertEqual(self.doc.tiers['nes'].spans[1].label, 'GPE')
        self.assertEqual(self.doc.tiers['nes'].spans[1].text, 'New York City')
        self.assertEqual(self.doc.tiers['nes'].spans[1].start, 24)
        self.assertEqual(self.doc.tiers['nes'].spans[1].end, 37)

        self.assertEqual(self.doc.tiers['nes'].spans[2].label, 'GPE')
        self.assertEqual(
            self.doc.tiers['nes'].spans[2].text, 'the United States')
        self.assertEqual(self.doc.tiers['nes'].spans[2].start, 50)
        self.assertEqual(self.doc.tiers['nes'].spans[2].end, 67)

        self.assertEqual(self.doc.tiers['nes'].spans[3].label, 'ORG')
        self.assertEqual(
            self.doc.tiers['nes'].spans[3].text, 'the Raytheon Corporation')
        self.assertEqual(self.doc.tiers['nes'].spans[3].start, 82)
        self.assertEqual(self.doc.tiers['nes'].spans[3].end, 106)


if __name__ == '__main__':
    unittest.main()
