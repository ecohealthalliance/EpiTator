#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

    def assertHasCounts(self, sent, counts):
        doc = AnnoDoc(sent)
        doc.add_tier(self.annotator)
        actuals = []
        expecteds = []
        for actual, expected in zip(doc.tiers['counts'].spans, counts):
            if expected.get('count'):
                actuals += [actual.metadata.get('count')]
                expecteds += [expected.get('count')]
            else:
                actuals += [None]
                expecteds += [None]
        self.assertEqual(actuals, expecteds)
        for actual, expected in zip(doc.tiers['counts'].spans, counts):
            test_utils.assertHasProps(actual.metadata, expected)

    def test_no_counts(self):
        doc = AnnoDoc('Fever')
        doc.add_tier(self.annotator)

    def test_false_positive_counts(self):
        examples = [
            'In the case of mosquito-borne diseases indoor spraying is a common intervention',
            'Measles - Democratic Republic of the Congo (Katanga) 2007.1775',
            'Meningitis - Democratic Republic of Congo [02] 970814010223',
            'On 11 / 16 / 1982 the The Last Unicorn was the most popular movie.'
        ]
        for example in examples:
            self.assertHasCounts(example, [])

    def test_verb_counts(self):
        examples = [
            ('it brings the number of cases reported to 28 in Jeddah since 27 March 2014', 28),
            ('There have been nine hundred and ninety-nine reported cases.', 999)
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
        examples = [('The number of deaths is 30', 30),
                    # Also test unicode
                    (u'The number of deaths is 30', 30),
                    ('Nine patients died last week', 9)]
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
            In total, there were five million three hundred and fifty eight thousand new cases last year.""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 2)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 222
            }
        )
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[1].metadata, {
                'count': 5358000
            }
        )

    def test_hospitalization_counts1(self):
        examples = [('33 were hospitalized', 33),
                    ('222 were admitted to hospitals with symptoms of diarrhea', 222)]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['counts']), 1)
            test_utils.assertHasProps(
                doc.tiers['counts'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['case', 'hospitalization']
                })

    def test_colon_delimited_counts(self):
        self.assertHasCounts("""
The 15 cases confirmed since the year began are as follows:

Deaths: 2
Hospitalizations: 5
Ongoing cases: 7
""", [
            {'count': 15, 'attributes': ['case', 'confirmed']},
            {'count': 2, 'attributes': ['case', 'death']},
            {'count': 5, 'attributes': ['case', 'hospitalization']},
            {'count': 7, 'attributes': ['case', 'ongoing']}])

    def test_age_elimination(self):
        doc = AnnoDoc(
            '1200 children under the age of 5 are afflicted with a mystery illness')
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 1200
            }
        )
        self.assertEqual(len(doc.tiers['counts'].spans), 1)

    def test_raw_counts(self):
        doc = AnnoDoc('There are 5 new ones.')
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[0].metadata, {
                'count': 5,
                'attributes': ['incremental']
            }
        )
        self.assertEqual(len(doc.tiers['counts'].spans), 1)

    def test_complex(self):
        sent = 'These 2 new cases bring to 4 the number stricken in California this year [2012].'
        counts = [
            {'count': 2, 'attributes': ['case', 'incremental']},
            {'count': 4, 'attributes': ['case']}
        ]
        self.assertHasCounts(sent, counts)

    def test_complex_2(self):
        sent = 'Two patients died out of four patients.'
        counts = [
            {'count': 2, 'attributes': ['case', 'death']},
            {'count': 4, 'attributes': ['case']}
        ]
        self.assertHasCounts(sent, counts)

    def test_cumulative(self):
        sent = 'In total nationwide, 613 cases of the disease have been reported as of 2 July 2014, with 63 deceased patients'
        counts = [
            {'count': 613, 'attributes': ['case', 'cumulative']},
            {'count': 63, 'attributes': ['case', 'death']}
        ]
        self.assertHasCounts(sent, counts)

    def test_cumulative_2(self):
        sent = 'it has already claimed about 455 lives in Guinea'
        counts = [
            {
                'count': 455,
                'attributes': ['approximate', 'case', 'cumulative', 'death']}
        ]
        self.assertHasCounts(sent, counts)

    def test_attributes(self):
        self.assertHasCounts('There have been 12 reported cases in Colorado. '
                             'There was one suspected case of bird flu in the country.',
                             [{'count': 12, 'attributes': ['case']},
                              {'count': 1, 'attributes': ['case', 'suspected']}])

    def test_attributes_2(self):
        self.assertHasCounts('The average number of cases reported annually is 600',
                             [{'count': 600, 'attributes': ['annual', 'average', 'case']}])

    def test_attributes_3(self):
        self.assertHasCounts("""
As of [Thu 7 Sep 2017], there have been a total of:
1715 laboratory-confirmed cases of MERS-CoV infection, including
690 deaths [reported case fatality rate 40.2 percent],
1003 recoveries, and 0 currently active cases/infections
        """, [
            {'count': 1715, 'attributes': ['case', 'confirmed', 'cumulative']},
            {'count': 690, 'attributes': ['case', 'death']},
            {'count': 1003, 'attributes': ['case', 'recovery']},
            {'count': 0, 'attributes': ['case', 'ongoing']}
        ])

    def test_misc(self):
        sent = """How many cases occured with 3.2 miles of Katanga Province?
                  Three fatalities have been reported."""
        counts = [
            {
                'count': 3,
                'attributes': ['case', 'death']}
        ]
        self.assertHasCounts(sent, counts)

    def test_distance_and_percentage_filtering(self):
        examples = [
            ('48 percent of the cases occured in Seattle', []),
            ('28 kilometers away [17.4 miles]', [])
        ]
        for example in examples:
            sent, counts = example
            self.assertHasCounts(sent, counts)

    def test_tokenization_edge_cases(self):
        """
        These examples triggered some bugs with word token alignment in the past.
        """
        examples = [
            ('These numbers include laboratory-confirmed, probable, and suspect cases and deaths of EVD.', []),
            ("""22 new cases of EVD, including 14 deaths, were reported as follows:
        Guinea, 3 new cases and 5 deaths; Liberia, 8 new cases with 7 deaths; and Sierra Leone 11 new cases and 2 deaths.
        """, [{'count': 22}, {'count': 14}, {'count': 3}, {'count': 5}, {'count': 8}, {'count': 7}, {'count': 11}, {'count': 2}])]
        for example in examples:
            sent, counts = example
            self.assertHasCounts(sent, counts)

    def test_internals(self):
        from epitator.count_annotator import search_spans_for_regex
        import epitator.result_aggregators as ra
        doc = AnnoDoc('Deaths: 2')
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
        self.assertHasCounts('The index case occured on January 22.', [
            {'count': 1, 'attributes': ['case']}])

    def test_singular_cases_2(self):
        self.assertHasCounts('A lassa fever case was reported in Hawaii', [
            {'count': 1, 'attributes': ['case']}])

    def test_singular_cases_3(self):
        self.assertHasCounts('They reported a patient infected with hepatitis B from a blood transfusion.',
                             [{'count': 1}])

    def test_singular_cases_4(self):
        self.assertHasCounts('the cases include a 27-year-old woman and 2 males, each of 37 years',
                             [{'count': 1}, {'count': 2}])

    def test_year_count(self):
        self.assertHasCounts("""As of [Sun 19 March 2017] (epidemiological week 11),
        a total of 1407 suspected cases of meningitis have been reported.""", [
            {'count': 1407}])

    def test_ranges(self):
        self.assertHasCounts('10 to 13 suspected cases of Ebola.', [
            {
                'count': 10,
                'attributes': ['case', 'min', 'suspected']
            }, {
                'count': 13,
                'attributes': ['case', 'max', 'suspected']
            }
        ])

    def test_count_suppression_fp(self):
        # Test that the count of 26 is not supressed by the 20 count
        doc = AnnoDoc('''
        20 in Montserrado County [Monrovia & environs); 26 deaths are among the confirmed cases.
        Foya, Lofa County, and New Kru Town [NW suburb of Monrovia],
        Montserrado County, remain the epicentres of this Ebola outbreak.
        ''')
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['counts']), 2)
        test_utils.assertHasProps(
            doc.tiers['counts'].spans[1].metadata, {
                'count': 26
            })

    def test_attribute_fp(self):
        # Make sure the count is not parsed as incremental becasue of the
        # new in New York.
        self.assertHasCounts('5 cases of Dengue in New York.', [
            {'attributes': ['case']}])

    # Currently failing. Uncomment after spacy model update.
    # def test_counts_with_spaces(self):
    #     doc = AnnoDoc("Ther were 565 749 new cases")
    #     doc.add_tier(self.annotator)
    #     actual_counts = [count.metadata['count']
    #                      for count in doc.tiers['counts'].spans
    #                      if 'case' in count.metadata['attributes']]
    #     print(actual_counts)

    # def test_count_table(self):
    #     doc = AnnoDoc('''
    #     Cases / 22 / 544 / 140 / 75 / 759
    #     Deaths / 14 / 291 / 128 / 48 / 467

    #     *New cases were reported between 25-29 Jun 2014

    #     The total number of cases is subject to change
    #     ''')
    #     doc.add_tier(self.annotator)
    #     self.assertEqual(len(doc.tiers['counts']), 10)


#     def test_count_list(self):
#         doc = AnnoDoc('''
# The 15 non-fatal cases confirmed across the state since the year began are as follows:
#
# ArithmeticError County - 1 case
#
# TypeError County - 1 case
#
# Python County - 2 cases
#
# Java County - 2 cases
#
# Scala County - 1 case
#
# Scheme County - 1 case
#
# Meteor County - 1 case
#
# Boolean County - 1 case (not including the fatality)
#
# Integer County - 3 cases
# ''')
#         doc.add_tier(self.annotator)
#         expected_counts = [
#             15,
#             1,
#             1,
#             2,
#             2,
#             1,
#             1,
#             1,
#             1,
#             3
#         ]
#         actual_counts = [count.metadata['count']
#                          for count in doc.tiers['counts'].spans
#                          if 'case' in count.metadata['attributes']]
#         self.assertSequenceEqual(actual_counts, expected_counts)
#
#     def test_count_list_2(self):
#         doc = AnnoDoc('Ica 562 cases, Chincha 17 cases, Nasca 152 cases, Palpa 409 cases, Pisco 299 cases.')
#         doc.add_tier(self.annotator)
#         expected_counts = [
#             562,
#             17,
#             152,
#             409,
#             299,
#         ]
#         actual_counts = [count.metadata['count']
#                          for count in doc.tiers['counts'].spans
#                          if 'case' in count.metadata['attributes']]
#         self.assertSequenceEqual(actual_counts, expected_counts)


if __name__ == '__main__':
    unittest.main()
