#!/usr/bin/env python
from __future__ import absolute_import
import unittest
import datetime
from epitator.annotator import AnnoDoc
from epitator.date_annotator import DateAnnotator


class DateAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = DateAnnotator()

    def test_no_times(self):
        text = 'I went to see her in a boat.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 0)

    def test_simple_date(self):
        text = 'I went to Chicago Friday, October 7th 2010.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 1)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 10, 7),
             datetime.datetime(2010, 10, 8)])

    def test_relative_date(self):
        text = 'Yesterday I went to the symphony.'
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 1)
        self.assertEqual(doc.tiers['dates'].spans[0].text, 'Yesterday')
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 10, 9),
             datetime.datetime(2010, 10, 10)])

    def test_duration_with_years(self):
        text = 'I lived there for three years, from 1999 until late 2001'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 1)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(1999, 1, 1),
             datetime.datetime(2002, 1, 1)])

    def test_inexact_range(self):
        text = 'From May to August of 2009 we languished there.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2009, 5, 1),
             datetime.datetime(2009, 8, 1)])

    def test_1950s(self):
        text = 'Adenoviruses, first isolated in the 1950s from explanted adenoid tissue.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(1950, 1, 1),
             datetime.datetime(1960, 1, 1)])

    def test_specificity(self):
        text = """He said the strain detected in the Cloppenburg district
        [Lower Saxony state] was the same as that found at another farm in November [2014]
        in Schleswig-Holstein state."""
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 1)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2014, 11, 1),
             datetime.datetime(2014, 12, 1)])
        self.assertEqual(
            doc.tiers['dates'].spans[0].text, 'November [2014')

    def test_dashes(self):
        text = 'Adenoviruses, first seen between 2010-1-1 and 2010-1-2'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 1, 1),
             datetime.datetime(2010, 1, 2)])

    def test_dashes_2(self):
        text = 'First seen between 2010-1-1 - 2011-1-1'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 1, 1),
             datetime.datetime(2011, 1, 1)])

    def test_dateparser_bug(self):
        # This triggers an exception in the dateparser library described in this
        # bug report:
        # https://github.com/scrapinghub/dateparser/issues/339
        # This only tests that the exception is handled.
        # The date range in the text is still not property parsed.
        text = "week 1 - 53, 2015"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

    def test_relative_date_range(self):
        text = "between Thursday and Friday"
        doc = AnnoDoc(text, date=datetime.datetime(2017,7,15))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 7, 13),
             datetime.datetime(2017, 7, 14)])

    def test_formatted_date(self):
        text = "08-FEB-17"
        doc = AnnoDoc(text, date=datetime.datetime(2017,7,15))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 2, 8),
             datetime.datetime(2017, 2, 9)])

if __name__ == '__main__':
    unittest.main()
