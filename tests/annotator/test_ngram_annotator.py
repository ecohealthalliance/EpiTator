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
        self.assertEqual(len(doc.tiers['1grams'].spans), 1)
        self.assertFalse('2grams' in doc.tiers)

        self.assertEqual(doc.tiers['ngrams'].spans[0].text, 'Hi')
        self.assertEqual(doc.tiers['1grams'].spans[0].text, 'Hi')

    def test_two_word_sentence(self):

        doc = AnnoDoc("Hi there")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['ngrams'].spans), 3)
        self.assertEqual(len(doc.tiers['1grams'].spans), 2)
        self.assertEqual(len(doc.tiers['2grams'].spans), 1)
        self.assertFalse('3grams' in doc.tiers)
        self.assertFalse('4grams' in doc.tiers)

        all_texts = set([span.text for n in range(1, 3)
                                   for span in doc.tiers[str(n) + 'grams'].spans])
        expected_texts = set(['Hi', 'there', 'Hi there'])
        self.assertEqual(all_texts, expected_texts)

        self.assertEqual(doc.tiers['ngrams'].spans[0].text, 'Hi')
        self.assertEqual(doc.tiers['ngrams'].spans[1].text, 'there')
        self.assertEqual(doc.tiers['ngrams'].spans[2].text, 'Hi there')
        self.assertEqual(doc.tiers['1grams'].spans[0].text, 'Hi')
        self.assertEqual(doc.tiers['1grams'].spans[1].text, 'there')
        self.assertEqual(doc.tiers['2grams'].spans[0].text, 'Hi there')


    def test_three_word_sentence_with_period(self):

        doc = AnnoDoc("Bears eat tacos.")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['ngrams'].spans), 10)
        self.assertEqual(len(doc.tiers['1grams'].spans), 4)
        self.assertEqual(len(doc.tiers['2grams'].spans), 3)
        self.assertEqual(len(doc.tiers['3grams'].spans), 2)
        self.assertEqual(len(doc.tiers['4grams'].spans), 1)
        self.assertFalse('5grams' in doc.tiers)
        self.assertFalse('6grams' in doc.tiers)
        self.assertFalse('7grams' in doc.tiers)

        all_texts = set([span.text for n in range(1, 5)
                                   for span in doc.tiers[str(n) + 'grams'].spans])
        expected_texts = set(['Bears', 'eat', 'tacos', '.', 'Bears eat',
                              'eat tacos', 'tacos.', 'Bears eat tacos',
                              'eat tacos.', 'Bears eat tacos.'])
        self.assertEqual(all_texts, expected_texts)

        self.assertEqual(doc.tiers['ngrams'].spans[0].text, 'Bears')
        self.assertEqual(doc.tiers['ngrams'].spans[1].text, 'eat')
        self.assertEqual(doc.tiers['ngrams'].spans[2].text, 'tacos')
        self.assertEqual(doc.tiers['ngrams'].spans[3].text, '.')
        self.assertEqual(doc.tiers['ngrams'].spans[4].text, 'Bears eat')
        self.assertEqual(doc.tiers['ngrams'].spans[5].text, 'eat tacos')
        self.assertEqual(doc.tiers['ngrams'].spans[6].text, 'tacos.')
        self.assertEqual(doc.tiers['ngrams'].spans[7].text, 'Bears eat tacos')
        self.assertEqual(doc.tiers['ngrams'].spans[8].text, 'eat tacos.')
        self.assertEqual(doc.tiers['ngrams'].spans[9].text, 'Bears eat tacos.')

        self.assertEqual(doc.tiers['1grams'].spans[0].text, 'Bears')
        self.assertEqual(doc.tiers['1grams'].spans[1].text, 'eat')
        self.assertEqual(doc.tiers['1grams'].spans[2].text, 'tacos')
        self.assertEqual(doc.tiers['1grams'].spans[3].text, '.')

        self.assertEqual(doc.tiers['2grams'].spans[0].text, 'Bears eat')
        self.assertEqual(doc.tiers['2grams'].spans[1].text, 'eat tacos')
        self.assertEqual(doc.tiers['2grams'].spans[2].text, 'tacos.')

        self.assertEqual(doc.tiers['3grams'].spans[0].text, 'Bears eat tacos')
        self.assertEqual(doc.tiers['3grams'].spans[1].text, 'eat tacos.')

        self.assertEqual(doc.tiers['4grams'].spans[0].text, 'Bears eat tacos.')


if __name__ == '__main__':
    unittest.main()