#!/usr/bin/env python
"""Tests for the CaseCountAnnotator that annotates a sentence with numerical
   instances of infections, hospitalizations and deaths."""

import sys
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.case_count_annotator import CaseCountAnnotator


class CaseCountAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.doc = AnnoDoc()
        self.annotator = CaseCountAnnotator()

    def test_verbal_counts(self):
        # TODO -- this example removed because it is long than the 2 intervening
        # optional words we're allowing in this pattern for now. We should find
        # and efficient way to match this example later.
        # ("it brings the number of cases reported in Jeddah since 27 Mar 2014 to 28", 28)
        examples = [("The number of cases exceeds 30", 30)]

        for example, actual_count in examples:
            self.doc.text = example
            self.doc.add_tier(self.annotator)
            self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
            self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, actual_count)

    def test_count_offsets(self):

        self.doc.text = "The ministry of health reports seventy five new patients were admitted"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 75)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 31)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 43)

    def test_written_numbers(self):

        self.doc.text = "two hundred and twenty two patients were admitted to hospitals"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 222)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 26)

    def test_hospital_counts(self):

        examples = [
            ("222 were admitted to hospitals with symptoms of diarrhea", 222),
            ("33 were hospitalized", 33)]

        for example, actual_count in examples:
            self.doc.text = example
            self.doc.add_tier(self.annotator)
            self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
            self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, actual_count)
            self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'hospitalizationCount')

    def test_death_counts(self):
        """We want to make sure that 'deathCount' is the type of the retained
           span here, as it is also a match for a 'caseCount' pattern."""

        self.doc.text = "Nine patients died last week"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 4)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 9)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'deathCount')

    def test_death_counts_pattern_problem(self):
        """The issue here is that CLIPS pattern library will tokenize colons
           separately from the preceding word."""

        self.doc.text = "Deaths: 2"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 8)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 9)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'deathCount')

    def test_numbers_last_pattern(self):
        """Make sure we can get the proper offsets if we have a numeric portion
           that comes at the end of the pattern."""

        self.doc.text = "The number of cases exceeds 30"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 28)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 30)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 30)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')

    def test_misc2(self):

        self.doc.text = "These 2 new cases bring to 4 stricken in California this year [2012]."
        self.doc.add_tier(self.annotator)

        # TODO what pattern is supposed to match '4' here?
        # self.assertEqual(len(self.doc.tiers['caseCounts']), 2)
        # self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 4)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)

    def test_duplicates(self):

        self.doc.text = "Two patients died out of four patients."
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 4)

    def test_cumulative(self):

        self.doc.text = "In total nationwide, 2613 cases of the disease have been reported as of 2 Jul 2014, with 63 deaths"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2613)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertTrue(self.doc.tiers['caseCounts'].spans[0].cumulative)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 63)

    def test_cumulative2(self):

        self.doc.text = "it has already claimed about 455 lives in Guinea"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 455)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'deathCount')
        self.assertTrue(self.doc.tiers['caseCounts'].spans[0].cumulative)

    def test_cumulative3(self):

        self.doc.text = "there have been a total of 176 cases of human infection with influenza A(H1N5) virus including 63 deaths in Egypt"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 2)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 176)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertTrue(self.doc.tiers['caseCounts'].spans[0].cumulative)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 63)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].type, 'deathCount')
        self.assertTrue(self.doc.tiers['caseCounts'].spans[1].cumulative)

    def test_value_modifier(self):

        self.doc.text = "The average number of cases reported annually is 600"
        self.doc.add_tier(self.annotator)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 600)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertFalse(self.doc.tiers['caseCounts'].spans[0].cumulative)
        self.assertListEqual(self.doc.tiers['caseCounts'].spans[0].modifiers, ['average', 'annual'])

    def test_adjective_or_verb(self):
        """Sometimes the parse tree is wrong and identifies adjectives as verbs,
           so check to make sure our patterns are coping with that."""

        self.doc.text = "There have been 12 reported cases in Colorado. There was one suspected case of bird flu in the country."
        self.doc.add_tier(self.annotator)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 12)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertFalse(self.doc.tiers['caseCounts'].spans[0].cumulative)
        self.assertListEqual(self.doc.tiers['caseCounts'].spans[0].modifiers, [])

        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].type, 'caseCount')
        self.assertFalse(self.doc.tiers['caseCounts'].spans[1].cumulative)
        self.assertListEqual(self.doc.tiers['caseCounts'].spans[1].modifiers, [])

    def test_hyphenated_numbers(self):

        self.doc.text = "There have been nine hundred ninety-nine reported cases."
        self.doc.add_tier(self.annotator)

        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 999)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertFalse(self.doc.tiers['caseCounts'].spans[0].cumulative)
        self.assertListEqual(self.doc.tiers['caseCounts'].spans[0].modifiers, [])


if __name__ == '__main__':
    unittest.main()

# TODO -- enable these once our aspirations have been achieved.

"""

    import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest
from diagnosis.feature_extractors import extract_counts

class TestCountExtractorAspirations(unittest.TestCase):
    def test_vague(self):
        example = "Hundreds of people have possibly contracted the disease cholera over the past few days"
        actual_count = 200
        count_obj = next(extract_counts(example), {})
        self.assertEqual(count_obj.get('type'), "caseCount")
        self.assertEqual(count_obj.get('aproximate'), True)
        self.assertEqual(count_obj.get('value'), actual_count)
    def test_location_association(self):
        example = "500 new MERS cases that Saudi Arabia has reported in the past 3 months appear to have occurred in hospitals"
        actual_count = 500
        count_obj = next(extract_counts(example), {})
        self.assertEqual(count_obj.get('location'), "Saudi Arabia")
        self.assertEqual(count_obj.get('value'), actual_count)
    def test_time_association(self):
        example = "Since 2001, the median annual number of cases in the U.S. was 60"
        actual_count = 60
        count_obj = next(extract_counts(example), {})
        self.assertEqual(count_obj.get('time'), "2001")
        self.assertEqual(count_obj.get('valueModifier'), "median")
        self.assertEqual(count_obj.get('value'), actual_count)
    # TODO -- this test should be re-enabled after we figure out how to run
    # patterns with lots of wildcards in them efficiently.
    # def test_misc(self):
    #     self.doc.text = "1200 children between the ages of 2-5 are afflicted with a mystery illness"
    #     self.doc.add_tier(self.annotator)

    #     self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
    #     self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 1200)

    def test_misc2(self):
        example = "These 2 new cases bring to 4 the number of people stricken in California this year [2012]."
        count_set = set([count['value'] for count in extract_counts(example)])
        self.assertSetEqual(count_set, set([2,4]))

"""
