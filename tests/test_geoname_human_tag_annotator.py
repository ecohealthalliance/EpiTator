#!/usr/bin/env python
"""Tests for the TokenAnnotator that annotates a sentence with tokens and their
offsets."""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.geoanme_human_tag_annotator import GeonameHumanTagAnnotator


class GeonameHumanTagAnnotatorTest(unittest.TestCase):

	def setUp(self):
		self.annotator = GeonameHumanTagAnnotator()

	def test_no_tags(self):

		text = 'I went to Chicago.'
		plain_text = text
		sentence = self.annotator.annotate(text=text)

		self.assertEqual(sentence.text, plain_text)

		self.assertEqual(len(sentence.tiers['gold_geonames'].spans), 0)


	def test_chicago(self):

		text = 'I went to <geo id="Chicago">Chicago</geo>.'
		plain_text = 'I went to Chicago.'
		sentence = self.annotator.annotate(text=text)

		self.assertEqual(sentence.text, plain_text)

		self.assertEqual(len(sentence.tiers['gold_geonames'].spans), 1)

		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].label, 'Chicago')
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].start, 10)
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].end, 17)

	def test_chicago_with_tags(self):

		text = 'I went <i>to</i> <geo id="Chicago">Chicago</geo>.'
		plain_text = 'I went to Chicago.'
		sentence = self.annotator.annotate(text=text)

		self.assertEqual(sentence.text, plain_text)

		self.assertEqual(len(sentence.tiers['gold_geonames'].spans), 1)

		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].label, 'Chicago')
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].start, 10)
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].end, 17)

	def test_with_broken_tags(self):

		text = """<i>If<i> <>you g<ggg"fddffd">o <aaaaa>to <geo id="Des Moines">Des Moines</geo>, stop by <geo id="St. Paul">St.<foo></dfdf.> Paul</geo> on the way."""
		plain_text = 'If you go to Des Moines, stop by St. Paul on the way.'
		sentence = self.annotator.annotate(text=text)

		self.assertEqual(sentence.text, plain_text)

		self.assertEqual(len(sentence.tiers['gold_geonames'].spans), 2)

		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].label, 'Des Moines')
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].start, 13)
		self.assertEqual(sentence.tiers['gold_geonames'].spans[0].end, 23)

		self.assertEqual(sentence.tiers['gold_geonames'].spans[1].label, 'St. Paul')
		self.assertEqual(sentence.tiers['gold_geonames'].spans[1].start, 33)
		self.assertEqual(sentence.tiers['gold_geonames'].spans[1].end, 41)
		
if __name__ == '__main__':
	unittest.main()