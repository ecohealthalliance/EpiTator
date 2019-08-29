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
        self.assertEqual(doc.tiers['dates'].spans, [])

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
        doc.add_tier(DateAnnotator(include_end_date=False))
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
             datetime.datetime(2009, 9, 1)])

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
             datetime.datetime(2010, 1, 3)])

    def test_dashes_2(self):
        text = 'First seen between 2010-1-1 - 2011-1-1'
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 1, 1),
             datetime.datetime(2011, 1, 2)])

    def test_dashes_3(self):
        doc = AnnoDoc('Distribution of reported yellow fever cases from 1 Jul 2017-17 Apr 2018')
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 7, 1),
             datetime.datetime(2018, 4, 18)])

    def test_dateparser_bug(self):
        # This triggers an exception in the dateparser library described in this
        # bug report:
        # https://github.com/scrapinghub/dateparser/issues/339
        # This only tests that the exception is handled.
        # The date range in the text is still not property parsed.
        text = "week 1 - 53, 2015"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)

    def test_dateparse_bug_2(self):
        # The current version of the date annotator tries to parse 72\n1994, which triggers an exception
        # in the dateparse library.
        doc = AnnoDoc("""
        Year Cases Fatal
        1991 46,320 697\n1992 31,870 208\n1993 6,833 72\n1994 1,785 16\n1995 2,160 23""")
        doc.add_tier(self.annotator)

    def test_relative_date_range(self):
        text = "between Thursday and Friday"
        doc = AnnoDoc(text, date=datetime.datetime(2017, 7, 15))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 7, 13),
             datetime.datetime(2017, 7, 15)])

    def test_relative_date_fp(self):
        text = "The maximum incubation period is 21 days."
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['dates'].spans, [])

    def test_formatted_date(self):
        text = "08-FEB-17"
        doc = AnnoDoc(text, date=datetime.datetime(2017, 7, 15))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 2, 8),
             datetime.datetime(2017, 2, 9)])

    def test_reversed_range_error_1(self):
        text = "24 to 94 years"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['dates'].spans, [])

    def test_reversed_range_error_2(self):
        text = "9 months to 9 years"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['dates'].spans, [])

    def test_reversed_range_error_3(self):
        text = "6350-65"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['dates'].spans, [])

    def test_day_of_week(self):
        text = "Sat 19 Aug 2017"
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 8, 19),
             datetime.datetime(2017, 8, 20)])

    def test_week_parsing(self):
        text = "AES had taken 13 lives in the 2nd week of October 2017."
        doc = AnnoDoc(text)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 10, 8),
             datetime.datetime(2017, 10, 15)])

    def test_count_table(self):
        doc = AnnoDoc('''
        Type / Suspected / Confirmed / Recovered / Ongoing / Total
        Cases / 8 / 34 / 18 / 16 / 70
        Deaths / 7 / 33 / 17 / 15 / 65
        ''')
        doc.add_tier(self.annotator)
        self.assertEqual(doc.tiers['dates'].spans, [])

    def test_date_table(self):
        doc = AnnoDoc('''
        Cumulative case data
        Report date / Cases / Deaths
        26 Jun 2017 / 190 / 10
        15 Sep 2017 / 319 / 14
        ''')
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 6, 26),
             datetime.datetime(2017, 6, 27)])
        self.assertEqual(
            doc.tiers['dates'].spans[1].datetime_range,
            [datetime.datetime(2017, 9, 15),
             datetime.datetime(2017, 9, 16)])

    def test_month_of_year(self):
        example = "Dengue cases were increasing in the 3rd month of the year [2017]."
        doc = AnnoDoc(example)
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 3, 1),
             datetime.datetime(2017, 4, 1)])

    def test_since_date(self):
        text = 'nearly 5000 cases have been reported since 1 Sep 2010.'
        doc = AnnoDoc(text, date=datetime.datetime(2010, 12, 10))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2010, 9, 1),
             datetime.datetime(2010, 12, 10)])

    def test_since_date_2(self):
        doc = AnnoDoc("Since April 6th 2013, 21 cases of infection have been confirmed.", date=datetime.datetime(2014, 12, 10))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2013, 4, 6),
             datetime.datetime(2014, 12, 10)])

    def test_long_entity_dates(self):
        # This tests dates that are extracted with peripheral text
        # by the current NER.
        doc = AnnoDoc("""
In the month of August 2017, there were a total of 3 laboratory confirmed cases.
For the first time since 1998, a case of yellow fever has been confirmed.
""", date=datetime.datetime(2017, 12, 10))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2017, 8, 1),
             datetime.datetime(2017, 9, 1)])
        self.assertEqual(
            doc.tiers['dates'].spans[1].datetime_range,
            [datetime.datetime(1998, 1, 1),
             datetime.datetime(2017, 12, 10)])

    def test_incorrect_date_grouping_bug(self):
        doc = AnnoDoc('''
A 31-year-old man from east Delhi's Mandawali succumbed to malaria at Safdarjung Hospital the 1st week of September [2016]. In July [2016], a 62-year-old man had died of the disease in northwest Delhi's Jyoti Nagar.''')
        doc.add_tier(self.annotator)

    def test_far_future_year_error(self):
        # 3120 was being parsed as a year which would cause a year out of rage error when creating a datetime object.
        doc = AnnoDoc("The cases from January to March [2011] eclipse the number of cases from the entire 2009 (2723) and 2010 (3120) [years].")
        doc.add_tier(self.annotator)

    def test_date_range(self):
        doc = AnnoDoc("The 7 new cases age between 17 and 70, and their onset dates vary between 19 May [2018] - 5 Jun [2018].")
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2018, 5, 19),
             datetime.datetime(2018, 6, 6)])

    def test_dateparser_bug_2(self):
        doc = AnnoDoc("One of the guys has already received a laboratory confirmation of the diagnosis of botulism 17.05.2018 year.")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['dates'].spans), 1)

    def test_relative_date_range_2(self):
        doc = AnnoDoc(
            "In the past 20 days 285 cases of swine flu have been reported across the state.",
            date=datetime.datetime(2018, 12, 21))
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(2018, 12, 1),
             datetime.datetime(2018, 12, 21)])

    def test_partial_year_range(self):
        doc = AnnoDoc("From 1912-17 some stuff happened.")
        doc.add_tier(self.annotator)
        self.assertEqual(
            doc.tiers['dates'].spans[0].datetime_range,
            [datetime.datetime(1912, 1, 1),
             datetime.datetime(1918, 1, 1)])

    def test_aware_datetime(self):
        doc = AnnoDoc(" trade Date: Fri 29 Sep 2018 13:31 BST Source: Express")
        doc.add_tier(self.annotator)
        self.assertEqual(
            [date.replace(tzinfo=None) for date in doc.tiers['dates'].spans[0].datetime_range],
            [datetime.datetime(2018, 9, 29, 13, 31),
             datetime.datetime(2018, 9, 30, 13, 31)])
