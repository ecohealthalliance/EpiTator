#!/usr/bin/env python
"""Tests for the NgramAnnotator"""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.ngram_annotator import NgramAnnotator


class NgramAnnotatorTest(unittest.TestCase):

    def setUp(self):

        self.annotator = NgramAnnotator()

    def test_one_word_sentence(self):

        doc = AnnoDoc("Hi")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['ngrams'].spans), 1)

        self.assertEqual(doc.tiers['ngrams'].spans[0].text, 'Hi')

    def test_two_word_sentence(self):

        doc = AnnoDoc("Hi there")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['ngrams'].spans), 3)

        self.assertEqual(doc.tiers['ngrams'].spans[0].text, 'Hi')
        self.assertEqual(doc.tiers['ngrams'].spans[1].text, 'Hi there')
        self.assertEqual(doc.tiers['ngrams'].spans[2].text, 'there')


    def test_three_word_sentence_with_period(self):

        doc = AnnoDoc("Bears eat tacos.")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['ngrams'].spans), 10)
        span_iter = iter(doc.tiers['ngrams'].spans)
        self.assertEqual(next(span_iter).text, 'Bears')
        self.assertEqual(next(span_iter).text, 'Bears eat')
        self.assertEqual(next(span_iter).text, 'Bears eat tacos')
        self.assertEqual(next(span_iter).text, 'Bears eat tacos.')
        self.assertEqual(next(span_iter).text, 'eat')
        self.assertEqual(next(span_iter).text, 'eat tacos')
        self.assertEqual(next(span_iter).text, 'eat tacos.')
        self.assertEqual(next(span_iter).text, 'tacos')
        self.assertEqual(next(span_iter).text, 'tacos.')
        self.assertEqual(next(span_iter).text, '.')

if __name__ == '__main__':
    unittest.main()