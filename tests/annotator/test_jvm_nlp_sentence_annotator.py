#!/usr/bin/env python
"""Tests for the SentenceAnnotator that annotates a doc with sentence offsets."""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.jvm_nlp_annotator import JVMNLPAnnotator


class SentenceAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = JVMNLPAnnotator(['sentences'])
        self.doc = AnnoDoc()

    def test_one_sentence(self):

        self.doc.text = "Hi Joe."
        sentence = self.annotator.annotate(self.doc)

        self.assertEqual(len(self.doc.tiers['sentences'].spans), 1)

        self.assertEqual(self.doc.tiers['sentences'].spans[0].text, 'Hi Joe.')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].label, 'Hi Joe.')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['sentences'].spans[0].end, 7)

    def test_two_sentences(self):

        self.doc.text = "Hi Joe. It's me, Jane."
        sentence = self.annotator.annotate(self.doc)

        self.assertEqual(len(self.doc.tiers['sentences'].spans), 2)

        self.assertEqual(self.doc.tiers['sentences'].spans[0].text, 'Hi Joe.')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].label, 'Hi Joe.')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['sentences'].spans[0].end, 7)

        self.assertEqual(self.doc.tiers['sentences'].spans[1].text, "It's me, Jane.")
        self.assertEqual(self.doc.tiers['sentences'].spans[1].label, "It's me, Jane.")
        self.assertEqual(self.doc.tiers['sentences'].spans[1].start, 8)
        self.assertEqual(self.doc.tiers['sentences'].spans[1].end, 22)

    # This differs from NLTK sentence tokenization in that trailing leading white
    # space is not considered to be part of the sentence.
    def test_odd_spacing(self):

        self.doc.text = "  \t      Hi Joe      .   \n \n \n \t  It's me, Jane   \t  .   \t  "
        sentence = self.annotator.annotate(self.doc)

        self.assertEqual(len(self.doc.tiers['sentences'].spans), 2)

        self.assertEqual(self.doc.tiers['sentences'].spans[0].text, 'Hi Joe      .')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].label, 'Hi Joe      .')
        self.assertEqual(self.doc.tiers['sentences'].spans[0].start, 9)
        self.assertEqual(self.doc.tiers['sentences'].spans[0].end, 22)

        self.assertEqual(self.doc.tiers['sentences'].spans[1].text, "It's me, Jane   \t  .")
        self.assertEqual(self.doc.tiers['sentences'].spans[1].label, "It's me, Jane   \t  .")
        self.assertEqual(self.doc.tiers['sentences'].spans[1].start, 34)
        self.assertEqual(self.doc.tiers['sentences'].spans[1].end, 54)


if __name__ == '__main__':
    unittest.main()
