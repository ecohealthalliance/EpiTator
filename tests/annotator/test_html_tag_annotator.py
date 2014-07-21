#!/usr/bin/env python
"""Tests for the TokenAnnotator that annotates a sentence with tokens and their
offsets."""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.html_tag_annotator import HTMLTagAnnotator


class HTMLTagAnnotatorTest(unittest.TestCase):


    def test_no_tags(self):

        annotator = HTMLTagAnnotator(['b', 'p'])

        text = 'I went to Chicago.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['html'].spans), 0)


    def test_bold(self):

        annotator = HTMLTagAnnotator(['b', 'p'])

        text = 'I see a <b>squirrel</b>.'
        plain_text = 'I see a squirrel.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 1)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'b')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'squirrel')
        self.assertEqual(doc.tiers['html'].spans[0].start, 8)
        self.assertEqual(doc.tiers['html'].spans[0].end, 16)

    def test_tightly_nested(self):

        annotator = HTMLTagAnnotator(['b', 'p', 'i'])

        text = 'There is a <b><i>dog</i></b> under the couch.'
        plain_text = 'There is a dog under the couch.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 2)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'i')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'dog')
        self.assertEqual(doc.tiers['html'].spans[0].start, 11)
        self.assertEqual(doc.tiers['html'].spans[0].end, 14)

        self.assertEqual(doc.tiers['html'].spans[1].label, 'b')
        self.assertEqual(doc.tiers['html'].spans[1].text, 'dog')
        self.assertEqual(doc.tiers['html'].spans[1].start, 11)
        self.assertEqual(doc.tiers['html'].spans[1].end, 14)

    def test_loosely_nested(self):

        annotator = HTMLTagAnnotator(['b', 'p', 'i'])

        text = 'There is a <b>big old <i>dog</i></b> under the couch.'
        plain_text = 'There is a big old dog under the couch.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 2)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'b')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'big old dog')
        self.assertEqual(doc.tiers['html'].spans[0].start, 11)
        self.assertEqual(doc.tiers['html'].spans[0].end, 22)

        self.assertEqual(doc.tiers['html'].spans[1].label, 'i')
        self.assertEqual(doc.tiers['html'].spans[1].text, 'dog')
        self.assertEqual(doc.tiers['html'].spans[1].start, 19)
        self.assertEqual(doc.tiers['html'].spans[1].end, 22)

    def test_paragraph_with_space(self):

        annotator = HTMLTagAnnotator(['b', 'p', 'i'])

        text = '<p>There is a fish under the tree.</p> <p>How odd!</p>'
        plain_text = 'There is a fish under the tree. How odd!'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 2)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'p')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'There is a fish under the tree.')
        self.assertEqual(doc.tiers['html'].spans[0].start, 0)
        self.assertEqual(doc.tiers['html'].spans[0].end, 31)

        self.assertEqual(doc.tiers['html'].spans[1].label, 'p')
        self.assertEqual(doc.tiers['html'].spans[1].text, 'How odd!')
        self.assertEqual(doc.tiers['html'].spans[1].start, 32)
        self.assertEqual(doc.tiers['html'].spans[1].end, 40)


    def test_paragraph_without_space(self):

        annotator = HTMLTagAnnotator(['b', 'p', 'i'])

        text = '<p>There is a fish under the tree.</p><p>How odd!</p>'
        plain_text = 'There is a fish under the tree. How odd!'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 2)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'p')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'There is a fish under the tree.')
        self.assertEqual(doc.tiers['html'].spans[0].start, 0)
        self.assertEqual(doc.tiers['html'].spans[0].end, 31)

        self.assertEqual(doc.tiers['html'].spans[1].label, 'p')
        self.assertEqual(doc.tiers['html'].spans[1].text, 'How odd!')
        self.assertEqual(doc.tiers['html'].spans[1].start, 32)
        self.assertEqual(doc.tiers['html'].spans[1].end, 40)

    def test_attrs(self):

        annotator = HTMLTagAnnotator(['a'])

        text = '<p>Click <a href="http://sample.com">here</a> to check it out.'
        plain_text = 'Click here to check it out.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, plain_text)
        self.assertEqual(len(doc.tiers['html'].spans), 1)

        self.assertEqual(doc.tiers['html'].spans[0].label, 'a')
        self.assertEqual(doc.tiers['html'].spans[0].text, 'here')
        self.assertEqual(doc.tiers['html'].spans[0].attrs['href'], 'http://sample.com')
        self.assertEqual(doc.tiers['html'].spans[0].start, 6)
        self.assertEqual(doc.tiers['html'].spans[0].end, 10)


if __name__ == '__main__':
    unittest.main()