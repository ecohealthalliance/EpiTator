#!/usr/bin/env python
"""
Tests our ability to annotate sentences with numerical
instances of infections, hospitalizations and deaths.
"""

import sys
import unittest
import test_utils

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.count_annotator import CountAnnotator

class TestCountAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = CountAnnotator()

    def test_no_counts(self):
        doc = AnnoDoc("Fever")
        doc.add_tier(self.annotator)

    def test_false_positive_counts(self):
        examples = [
            "Measles - Democratic Republic of the Congo (Katanga) 2007.1775",
            "Meningitis - Democratic Republic of Congo (02) 970814010223"
        ]
        for example in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts']), 0)

    def test_verb_counts(self):
        examples = [
            ("it brings the number of cases reported to 28 in Jeddah since 27 Mar 2014", 28),
            ("There have been nine hundred ninety-nine reported cases.", 999)
        ]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts']), 1)
            test_utils.assertHasProps(
                doc.tiers['counts'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['case']
                })

    def test_death_counts(self):
        examples = [("The number of deaths is 30", 30),
                    # Also test unicode
                    (u"The number of deaths is 30", 30),
                    ("Nine patients died last week", 9)]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts']), 1)
            test_utils.assertHasProps(
                doc.tiers['counts'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['case', 'death']
                })

    def test_offsets(self):
        doc = AnnoDoc("The ministry of health reports seventy five new patients were admitted")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 1)
        self.assertEqual(doc.tiers['counts'].spans[0].start, 31)
        self.assertEqual(doc.tiers['counts'].spans[0].end, 56)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count' : 75
            }
        )

    def test_written_numbers(self):
        doc = AnnoDoc("two hundred and twenty two patients were admitted to hospitals")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 1)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 222
            }
        )

    def test_hospitalization_counts1(self):
        examples = [("33 were hospitalized", 33),
                    ("222 were admitted to hospitals with symptoms of diarrhea", 222)]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts']), 1)
            test_utils.assertHasProps(
                doc.tiers['counts'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['hospitalization']
                })

    def test_death_counts_pattern_problem(self):
        """The issue here is that CLIPS pattern library will tokenize colons
           separately from the preceding word."""

        doc = AnnoDoc("Deaths: 2")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['counts']), 1)
        self.assertEqual(doc.tiers['counts'].spans[0].start, 0)
        self.assertEqual(doc.tiers['counts'].spans[0].end, 9)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 2
            })

    def test_age_elimination(self):
        doc = AnnoDoc("1200 children under the age of 5 are afflicted with a mystery illness")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count' : 1200
            }
        )
        self.assertEqual(len(doc.tiers['counts'].spans), 1)

    def test_raw_counts(self):
        doc = AnnoDoc("There are 5 new ones.")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count' : 5,
                'attributes': ['incremental']
            }
        )
        self.assertEqual(len(doc.tiers['counts'].spans), 1)

    def test_complex(self):
        examples = [
            ("These 2 new cases bring to 4 the number stricken in California this year [2012].", [
                {'count': 2, 'attributes': ['case', 'incremental']},
                {'count': 4, 'attributes': ['case']},
            ]),
            ("Two patients died out of four patients.", [
                {'count': 2, 'attributes': ['case', 'death']},
                {'count': 4, 'attributes': ['case']},
            ]),
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_cumulative(self):
        examples = [
            ("In total nationwide, 2613 cases of the disease have been reported as of 2 Jul 2014, with 63 deaths", [
                {'count': 2613, 'attributes': ['case', 'cumulative']},
                {'count': 63, 'attributes': ['case', 'death']}
            ]), 
            ("it has already claimed about 455 lives in Guinea", [
                {'count': 455, 'attributes': ['approximate', 'case', 'cumulative', 'death']}
            ])
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_attributes(self):
        examples= [
            ("There have been 12 reported cases in Colorado. " +
            "There was one suspected case of bird flu in the country.", [
                { 'count': 12, 'attributes': ['case'] },
                { 'count': 1, 'attributes': ['case', 'suspected'] }
            ]),
            ("The average number of cases reported annually is 600", [
                { 'count': 600, 'attributes': ['annual', 'average', 'case'] }
            ])
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

if __name__ == '__main__':
    unittest.main()
