#!/usr/bin/env python
"""Tests for the JVMNLPAnnotator that annotates a sentence with data from a
webservice providing Stanford NLP results.

As these tests require the presence of a well-running webservice, they may be
considered more of an integration test than a unit test.

The code for the webservice required is github.com/ecohealthalliance/jvm-nlp
"""

import sys
import unittest
import datetime

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.jvm_nlp_annotator import JVMNLPAnnotator


class JVMNLPAnnotatorTest(unittest.TestCase):

    def test_no_times(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I went to see her in a boat.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 0)

    def test_simple_date(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I went to Chicago Friday, October 7th 2010.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)
        self.assertEqual(doc.tiers['times'].spans[0].label, '2010-10-07')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'Friday, October 7th 2010')
        self.assertEqual(doc.tiers['times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['times'].spans[0].end, 42)

    def test_relative_date(self):

        annotator = JVMNLPAnnotator(['times'])

        text = "Tomorrow I'm going to the symphony."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)
        self.assertEqual(doc.tiers['times'].spans[0].label, '2010-10-11')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'Tomorrow')
        self.assertEqual(doc.tiers['times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['times'].spans[0].end, 8)

    def test_relative_dates(self):

        annotator = JVMNLPAnnotator(['times'])

        text = "Tomorrow I'm going to the symphony. In five days from now I'll wish it was yesterday."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 3)

        self.assertEqual(doc.tiers['times'].spans[0].label, '2010-10-11')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'Tomorrow')
        self.assertEqual(doc.tiers['times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['times'].spans[0].end, 8)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DATE')

        self.assertEqual(doc.tiers['times'].spans[1].label, '2010-10-15')
        self.assertEqual(doc.tiers['times'].spans[1].text, 'five days from now')
        self.assertEqual(doc.tiers['times'].spans[1].start, 39)
        self.assertEqual(doc.tiers['times'].spans[1].end, 57)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'DATE')

        self.assertEqual(doc.tiers['times'].spans[2].label, '2010-10-09')
        self.assertEqual(doc.tiers['times'].spans[2].text, 'yesterday')
        self.assertEqual(doc.tiers['times'].spans[2].start, 75)
        self.assertEqual(doc.tiers['times'].spans[2].end, 84)
        self.assertEqual(doc.tiers['times'].spans[2].type, 'DATE')

    def test_season(self):

        annotator = JVMNLPAnnotator(['times'])

        text = "Last summer I went to Lagos."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)

        self.assertEqual(doc.tiers['times'].spans[0].label, '2009-SU')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'Last summer')
        self.assertEqual(doc.tiers['times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['times'].spans[0].end, 11)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DATE')

    def test_extracted_reference_date(self):

        annotator = JVMNLPAnnotator(['times'])

        text = '10/10/14 It was 11am yesterday when I went to the beach. Tomorrow I head home.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 3)

        self.assertEqual(doc.tiers['times'].spans[0].label, '2014-10-10')
        self.assertEqual(doc.tiers['times'].spans[0].text, '10/10/14')
        self.assertEqual(doc.tiers['times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['times'].spans[0].end, 8)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DATE')

        self.assertEqual(doc.tiers['times'].spans[1].label, '2014-10-09T11:00')
        self.assertEqual(doc.tiers['times'].spans[1].text, '11am yesterday')
        self.assertEqual(doc.tiers['times'].spans[1].start, 16)
        self.assertEqual(doc.tiers['times'].spans[1].end, 30)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'TIME')

        self.assertEqual(doc.tiers['times'].spans[2].label, '2014-10-11')
        self.assertEqual(doc.tiers['times'].spans[2].text, 'Tomorrow')
        self.assertEqual(doc.tiers['times'].spans[2].start, 57)
        self.assertEqual(doc.tiers['times'].spans[2].end, 65)
        self.assertEqual(doc.tiers['times'].spans[2].type, 'DATE')

    def test_time(self):

        annotator = JVMNLPAnnotator(['times'])

        text = '10/10/14 I saw him at 3 in the afternoon.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 2)

        self.assertEqual(doc.tiers['times'].spans[1].label, '2014-10-10T15:00')
        self.assertEqual(doc.tiers['times'].spans[1].text, '3 in the afternoon')
        self.assertEqual(doc.tiers['times'].spans[1].start, 22)
        self.assertEqual(doc.tiers['times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'TIME')
        self.assertEqual(doc.tiers['times'].spans[1].timePoint.year, 2014)
        self.assertEqual(doc.tiers['times'].spans[1].timePoint.month, 10)
        self.assertEqual(doc.tiers['times'].spans[1].timePoint.date, 10)
        self.assertEqual(doc.tiers['times'].spans[1].timePoint.hour, 15)

    def test_duration(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I lived there for three years while getting my BA.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)

        self.assertEqual(doc.tiers['times'].spans[0].label, 'P3Y')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DURATION')

    def test_duration_with_years(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I lived there for three years, from 1999 until 2001'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 3)

        self.assertEqual(doc.tiers['times'].spans[0].label, 'P3Y')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DURATION')

        self.assertEqual(doc.tiers['times'].spans[1].label, '1999')
        self.assertEqual(doc.tiers['times'].spans[1].text, '1999')
        self.assertEqual(doc.tiers['times'].spans[1].start, 36)
        self.assertEqual(doc.tiers['times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'DATE')

        self.assertEqual(doc.tiers['times'].spans[2].label, '2001')
        self.assertEqual(doc.tiers['times'].spans[2].text, '2001')
        self.assertEqual(doc.tiers['times'].spans[2].start, 47)
        self.assertEqual(doc.tiers['times'].spans[2].end, 51)
        self.assertEqual(doc.tiers['times'].spans[2].type, 'DATE')

    def test_duration_with_years(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I lived there for three years, from 1999 until late 2001'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 3)

        self.assertEqual(doc.tiers['times'].spans[0].label, 'P3Y')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DURATION')
        self.assertEqual(doc.tiers['times'].spans[0].timeDuration.label, 'P3Y')

        self.assertEqual(doc.tiers['times'].spans[1].label, '1999')
        self.assertEqual(doc.tiers['times'].spans[1].text, '1999')
        self.assertEqual(doc.tiers['times'].spans[1].start, 36)
        self.assertEqual(doc.tiers['times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'DATE')
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.begin.year, 1999)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.begin.month, 1)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.begin.date, 1)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.end.year, 1999)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.end.month, 12)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.end.date, 31)

        self.assertEqual(doc.tiers['times'].spans[2].label, '2001')
        self.assertEqual(doc.tiers['times'].spans[2].text, 'late 2001')
        self.assertEqual(doc.tiers['times'].spans[2].start, 47)
        self.assertEqual(doc.tiers['times'].spans[2].end, 56)
        self.assertEqual(doc.tiers['times'].spans[2].type, 'DATE')
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.mod, 'LATE')
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.end.mod, None)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.begin.year, 2001)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.begin.month, 1)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.begin.date, 1)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.end.year, 2001)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.end.month, 12)
        self.assertEqual(doc.tiers['times'].spans[2].timeRange.end.date, 31)

    def test_modifier_late(self):

        annotator = JVMNLPAnnotator(['times'])

        text = '1/1/2000 I lived there at the end of the 1920s.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 2)

        self.assertEqual(doc.tiers['times'].spans[1].label, '192X')
        self.assertEqual(doc.tiers['times'].spans[1].text, 'the end of the 1920s')
        self.assertEqual(doc.tiers['times'].spans[1].start, 26)
        self.assertEqual(doc.tiers['times'].spans[1].end, 46)
        self.assertEqual(doc.tiers['times'].spans[1].type, 'DATE')
        self.assertEqual(hasattr(doc.tiers['times'].spans[1], 'timePoint'), False)
        self.assertEqual(doc.tiers['times'].spans[1].timeRange.mod, 'LATE')

    def test_modifier_less_than(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I lived there for less than three years.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)

        self.assertEqual(doc.tiers['times'].spans[0].label, 'P3Y')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'less than three years')
        self.assertEqual(doc.tiers['times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['times'].spans[0].end, 39)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DURATION')
        self.assertEqual(doc.tiers['times'].spans[0].timeDuration.mod, 'LESS_THAN')

    def test_set(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'We meet for coffee every Tuesday.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)

        self.assertEqual(doc.tiers['times'].spans[0].label, 'XXXX-WXX-2')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'every Tuesday')
        self.assertEqual(doc.tiers['times'].spans[0].start, 19)
        self.assertEqual(doc.tiers['times'].spans[0].end, 32)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'SET')
        self.assertEqual(doc.tiers['times'].spans[0].timeSet.mod, None)

    def test_first_three_months(self):

        annotator = JVMNLPAnnotator(['times'])

        text = 'I arrived during the 1st three months of 2014, so yeah.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['times'].spans), 1)

        print doc.tiers['times'].spans[0]

        self.assertEqual(doc.tiers['times'].spans[0].label, '2014 INTERSECT P3M')
        self.assertEqual(doc.tiers['times'].spans[0].text, 'three months of 2014')
        self.assertEqual(doc.tiers['times'].spans[0].start, 25)
        self.assertEqual(doc.tiers['times'].spans[0].end, 45)
        self.assertEqual(doc.tiers['times'].spans[0].type, 'DATE')


if __name__ == '__main__':
    unittest.main()
