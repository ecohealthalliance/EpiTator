#!/usr/bin/env python
"""
Tests our ability to annotate sentences with numerical
instances of infections, hospitalizations and deaths.
"""
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.count_annotator import CountAnnotator
from six.moves import zip


class TestCountAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = CountAnnotator()

    def test_no_counts(self):
        doc = AnnoDoc("Fever")
        doc.add_tier(self.annotator)

    def test_false_positive_counts(self):
        examples = [
            "Measles - Democratic Republic of the Congo (Katanga) 2007.1775",
            "Meningitis - Democratic Republic of Congo [02] 970814010223"
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
        doc = AnnoDoc(
            "The ministry of health reports seventy five new patients were admitted")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 1)
        self.assertEqual(doc.tiers['counts'].spans[0].start, 31)
        self.assertEqual(doc.tiers['counts'].spans[0].end, 56)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 75
            }
        )

    def test_written_numbers(self):
        doc = AnnoDoc("""
            Two hundred and twenty two patients were admitted to hospitals.
            In total, there were five million three hundred and forty eight thousand new cases last year.""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 2)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 222
            }
        )
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[1].metadata, {
                'count': 5348000
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

    def test_colon_delimited_counts(self):
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
        doc = AnnoDoc(
            "1200 children under the age of 5 are afflicted with a mystery illness")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 1200
            }
        )
        self.assertEqual(len(doc.tiers['counts'].spans), 1)

    def test_raw_counts(self):
        doc = AnnoDoc("There are 5 new ones.")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 5,
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
            ("In total nationwide, 613 cases of the disease have been reported as of 2 Jul 2014, with 63 deaths", [
                {'count': 613, 'attributes': ['case', 'cumulative']},
                {'count': 63, 'attributes': ['case', 'death']}
            ]),
            ("it has already claimed about 455 lives in Guinea", [
                {'count': 455, 'attributes': [
                    'approximate', 'case', 'cumulative', 'death']}
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
        examples = [
            ("There have been 12 reported cases in Colorado. " +
             "There was one suspected case of bird flu in the country.", [
                 {'count': 12, 'attributes': ['case']},
                 {'count': 1, 'attributes': ['case', 'suspected']}
             ]),
            ("The average number of cases reported annually is 600", [
                {'count': 600, 'attributes': ['annual', 'average', 'case']}
            ])
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_misc(self):
        examples = [
            ("""How many cases occured with 3.2 miles of Katanga Province?
                Three fatalities have been reported.""", [{'count': 3}])
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_distance_and_percentage_filtering(self):
        examples = [
            ("48 percent of the cases occured in Seattle", []),
            ("28 kilometers away [17.4 miles]", [])
        ]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_tokenization_edge_cases(self):
        """
        These examples triggered some bugs with word token alignment in the past.
        """
        examples = [
            ("These numbers include laboratory-confirmed, probable, and suspect cases and deaths of EVD.", []),
            ("""22 new cases of EVD, including 14 deaths, were reported as follows:
        Guinea, 3 new cases and 5 deaths; Liberia, 8 new cases with 7 deaths; and Sierra Leone 11 new cases and 2 deaths.
        """, [{'count': 22}, {'count': 14}, {'count': 3}, {'count': 5}, {'count': 8}, {'count': 7}, {'count': 11}, {'count': 2}])]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    def test_internals(self):
        from epitator.count_annotator import search_spans_for_regex
        import epitator.result_aggregators as ra
        doc = AnnoDoc("Deaths: 2")
        doc.add_tier(self.annotator)
        ra.follows([
            search_spans_for_regex(
                'deaths(\s?:)?', doc.tiers['spacy.tokens'].spans),
            search_spans_for_regex('\d+', doc.tiers['spacy.tokens'].spans)])

    def test_full_article(self):
        """
        Tests a full length article
        """
        example = """
Last week an outbreak of the plague was reported by two different HHS departments in California.
The first case involved a 72 year old man with 3 brothers and 1 sister.
They should be tested in case they were infected.
He had visited between 2 and 4 different countries in the last year.
On 1/2/2017 he traveled to Zambia stopping at the lat/long: 121.125123, -90.234512 for a total of 7 days.
When asked what his favorite number was he responded, "883814019938"
though there has been heavy speculation that the actual favorite is 7003.3383.

When searching within a 7 mile radius of the epicenter there were:
    5 cases in Allaghaney resulting in 2 deaths
    19 cases in The Little Town of Washington causing 8 deaths
    2 cases in North San Juan which resulted in the spontanious existance of 1 supernatural being

Health professionals have said that there is only a 12 percent chance these are accurate.
The directory of Nevada County HHS was quoted as saying,
"fifty thousand and twelve, four hundred and twelve, seventy three, one thousand, two hundred and sixteen".
Concerned citizens have said, "50,012, 412, 73, 200 and 16"
"""
        expected_counts = [
            1,
            5,
            2,
            19,
            8,
            2
        ]
        doc = AnnoDoc(example)
        doc.add_tier(self.annotator)
        actual_counts = [count.metadata['count']
                         for count in doc.tiers['counts'].spans
                         if 'case' in count.metadata['attributes']]
        self.assertSequenceEqual(actual_counts, expected_counts)

    def test_singular_cases(self):
        examples = [
            ("The index case occured on January 22.", [{'count': 1}]),
            ("A lassa fever case was reported in Hawaii", [{'count': 1}])]
        for example in examples:
            sent, counts = example
            doc = AnnoDoc(sent)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts'].spans), len(counts))
            for actual, expected in zip(doc.tiers['counts'].spans, counts):
                test_utils.assertHasProps(actual.metadata, expected)

    # def test_year_count(self):
    #     doc = AnnoDoc("""As of [Sun 19 Mar 2017] (epidemiological week 11),
    #     a total of 1407 suspected cases of meningitis have been reported.""")
    #     doc.add_tier(self.annotator)
    #     self.assertEqual(len(doc.tiers['counts']), 1)
    #     test_utils.assertHasProps(
    #         doc.tiers['counts'].spans[0].metadata, {
    #             'count': 1407
    #         })


if __name__ == '__main__':
    unittest.main()
