#!/usr/bin/env python
"""Tests for the JVMNLPAnnotator that annotates a sentence with data from a
webservice providing Stanford NLP results.

As these tests require the presence of a well-running webservice, they may be
considered more of an integration test than a unit test.

The code for the webservice required is github.com/ecohealthalliance/jvm-nlp
"""
import unittest
import datetime
from epitator.annotator import AnnoDoc
from epitator.jvm_nlp_annotator import JVMNLPAnnotator


class JVMNLPAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = JVMNLPAnnotator(['times'])

    def test_no_times(self):
        text = 'I went to see her in a boat.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 0)

    def test_simple_date(self):
        text = 'I went to Chicago Friday, October 7th 2010.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2010-10-07')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'Friday, October 7th 2010')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 42)

    def test_relative_date(self):
        text = "Tomorrow I'm going to the symphony."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2010-10-11')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].text, 'Tomorrow')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 8)

    def test_relative_dates(self):
        text = "Tomorrow I'm going to the symphony. In five days from now I'll wish it was yesterday."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 3)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2010-10-11')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].text, 'Tomorrow')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 8)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DATE')

        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].label, '2010-10-15')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].text, 'five days from now')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 39)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 57)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'DATE')

        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].label, '2010-10-09')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].text, 'yesterday')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].start, 75)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].end, 84)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].type, 'DATE')

    def test_season(self):
        text = "Last summer I went to Lagos."
        doc = AnnoDoc(text, date=datetime.datetime(2010, 10, 10))
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, '2009-SU')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'Last summer')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 11)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DATE')

    def test_extracted_reference_date(self):
        text = '10/10/14 It was 11am yesterday when I went to the beach. Tomorrow I head home.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 3)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2014-10-10')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].text, '10/10/14')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 0)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 8)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DATE')

        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].label, '2014-10-09T11:00')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].text, '11am yesterday')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 16)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 30)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'TIME')

        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].label, '2014-10-11')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].text, 'Tomorrow')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].start, 57)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].end, 65)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].type, 'DATE')

    def test_time(self):
        text = '10/10/14 I saw him at 3 in the afternoon.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 2)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].label, '2014-10-10T15:00')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].text, '3 in the afternoon')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 22)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'TIME')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timePoint.year, 2014)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timePoint.month, 10)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timePoint.date, 10)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timePoint.hour, 15)

    def test_duration(self):
        text = 'I lived there for three years while getting my BA.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, 'P3Y')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DURATION')

    def test_duration_with_years(self):
        text = 'I lived there for three years, from 1999 until 2001'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 3)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, 'P3Y')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DURATION')

        self.assertEqual(doc.tiers['stanford.times'].spans[1].label, '1999')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].text, '1999')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 36)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'DATE')

        self.assertEqual(doc.tiers['stanford.times'].spans[2].label, '2001')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].text, '2001')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].start, 47)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].end, 51)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].type, 'DATE')

    def test_duration_with_years2(self):
        text = 'I lived there for three years, from 1999 until late 2001'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 3)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, 'P3Y')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'three years')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 29)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DURATION')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].timeDuration.label, 'P3Y')

        self.assertEqual(doc.tiers['stanford.times'].spans[1].label, '1999')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].text, '1999')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 36)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 40)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'DATE')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.begin.year, 1999)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.begin.month, 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.begin.date, 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.end.year, 1999)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.end.month, 12)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.end.date, 31)

        self.assertEqual(doc.tiers['stanford.times'].spans[2].label, '2001')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].text, 'late 2001')
        self.assertEqual(doc.tiers['stanford.times'].spans[2].start, 47)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].end, 56)
        self.assertEqual(doc.tiers['stanford.times'].spans[2].type, 'DATE')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.mod, 'LATE')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.end.mod, None)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.begin.year, 2001)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.begin.month, 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.begin.date, 1)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.end.year, 2001)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.end.month, 12)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[2].timeRange.end.date, 31)

    def test_modifier_late(self):
        text = '1/1/2000 I lived there at the end of the 1920s.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 2)

        self.assertEqual(doc.tiers['stanford.times'].spans[1].label, '192X')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].text, 'the end of the 1920s')
        self.assertEqual(doc.tiers['stanford.times'].spans[1].start, 26)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].end, 46)
        self.assertEqual(doc.tiers['stanford.times'].spans[1].type, 'DATE')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[1], 'timePoint'), False)
        self.assertEqual(
            doc.tiers['stanford.times'].spans[1].timeRange.mod, 'LATE')

    def test_modifier_less_than(self):
        text = 'I lived there for less than three years.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, 'P3Y')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'less than three years')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 18)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 39)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'DURATION')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].timeDuration.mod, 'LESS_THAN')

    def test_set(self):
        text = 'We meet for coffee every Tuesday.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, 'XXXX-WXX-2')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'every Tuesday')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].start, 19)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].end, 32)
        self.assertEqual(doc.tiers['stanford.times'].spans[0].type, 'SET')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].timeSet.mod, None)

    def test_first_since(self):
        text = 'In the 1st three months of 2014, that was it.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2014 INTERSECT P3M')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'three months of 2014')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timePoint'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeRange'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeDuration'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeSet'), False)

    def test_previously(self):
        text = 'We previously developed the Virochip (University of California, San Francisco) as a broad-spectrum surveillance assay for identifying viral causes of unknown acute and chronic illnesses.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, 'PAST_REF')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'previously')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timePoint'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeRange'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeDuration'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeSet'), False)

    def test_future(self):
        text = 'Future large-scale studies of TMAdV seroepidemiology will be needed to better understand transmission of TMAdV between monkeys and humans.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, 'FUTURE_REF')
        self.assertEqual(doc.tiers['stanford.times'].spans[0].text, 'Future')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timePoint'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeRange'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeDuration'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeSet'), False)

    def test_inexact_range(self):
        text = 'From May to August of 2009 we languished there.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, 'XXXX-05/2009-08')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'From May to August of 2009')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timePoint'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeRange'), True)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeDuration'), True)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeSet'), False)

    def test_1950s(self):
        text = 'Adenoviruses, first isolated in the 1950s from explanted adenoid tissue.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, '195X')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'the 1950s')
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timePoint'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeRange'), True)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeDuration'), False)
        self.assertEqual(
            hasattr(doc.tiers['stanford.times'].spans[0], 'timeSet'), False)

    def test_intersect(self):
        """We see some labels like "OFFSET P-1D INTERSECT 2015-01-01" for phrases
        like "yesterday, 1 Jan 2015." We want to make sure we take only the date
        and not the "intersect" property."""
        text = 'I went there yesterday, 1 Jan 2015.'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].label, '2015-01-01')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'yesterday, 1 Jan 2015')

    def test_specificity(self):
        text = 'He said the strain detected in the Cloppenburg district [Lower Saxony state] was the same as that found at another farm in November [2014] in Schleswig-Holstein state.'

        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

        self.assertEqual(doc.text, text)

        self.assertEqual(len(doc.tiers['stanford.times'].spans), 1)

        self.assertEqual(doc.tiers['stanford.times'].spans[0].label, '2014-11')
        self.assertEqual(
            doc.tiers['stanford.times'].spans[0].text, 'November [2014')


if __name__ == '__main__':
    unittest.main()
