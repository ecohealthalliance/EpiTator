#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
These are tests for InfectionAnnotator which don't currently run. They are
generally previously-implemented features from CountAnnotator which have not
yet been implemented in InfectionAnnotator. Tests will be ordered by
implementation priority at some future time.
"""
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.infection_annotator import InfectionAnnotator
from six.moves import zip


class TestInfectionAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = InfectionAnnotator(inclusion_filter=None)

    def assertHasCounts(self, sent, counts):
        doc = AnnoDoc(sent)
        doc.add_tier(self.annotator)
        actuals = []
        expecteds = []
        for actual, expected in zip(doc.tiers['infections'].spans, counts):
            if expected.get('count'):
                actuals += [actual.metadata.get('count')]
                expecteds += [expected.get('count')]
            else:
                actuals += [None]
                expecteds += [None]
        self.assertEqual(actuals, expecteds)
        for actual, expected in zip(doc.tiers['infections'].spans, counts):
            test_utils.assertMetadataContents(actual.metadata, expected)

# TODO: We don't look for this formulation.
    def test_verb_counts(self):
        examples = [
            ('This brings the number of cases reported to 28 in Jeddah since 27 March 2014.', 28),
            ('There have been nine hundred and ninety-nine reported cases.', 999)
        ]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['infections']), 1)
            test_utils.assertMetadataContents(
                doc.tiers['infections'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['infection']
                })

    # TODO: Find a way to reach "30"
    def test_death_counts(self):
        examples = [('The number of deaths is 30', 30),
                    # Also test unicode
                    (u'The number of deaths is 30', 30),
                    ('Nine patients died last week', 9)]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['infections']), 1)
            test_utils.assertHasProps(
                doc.tiers['infections'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['infection', 'death']
                })

# TODO: I'm not concerned about this.
    def test_written_numbers(self):
        doc = AnnoDoc("""
            Two hundred and twenty two patients were admitted to hospitals.
            In total, there were five million three hundred and fifty eight thousand new cases last year.""")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['infections']), 2)
        test_utils.assertMetadataContents(
            doc.tiers['infections'].spans[0].metadata, {
                'count': 222, 'attributes': ['hospitalization']
            }
        )
        test_utils.assertMetadataContents(
            doc.tiers['infections'].spans[1].metadata, {
                'count': 5358000, 'attributes': ['infection']
            },
        )

# TODO: This test currently fails because we do not look for the form "[number-noun] [verb]".
    def test_hospitalization_counts1(self):
        examples = [('33 were hospitalized', 33),
                    ('222 were admitted to hospitals with symptoms of diarrhea', 222)]
        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['infections']), 1)
            test_utils.assertMetadataContents(
                doc.tiers['infections'].spans[0].metadata, {
                    'count': actual_count,
                    'attributes': ['hospitalization']
                })

    # We aren't including this test for now -- it's not even clear from context that this would be an infection we'd want to annotate.
    def test_raw_counts(self):
        doc = AnnoDoc('There are 5 new ones.')
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['infections'].spans[0].metadata, {
                'count': 5,
                'attributes': ['incremental']
            }
        )
        self.assertEqual(len(doc.tiers['infections'].spans), 1)

    #  WE DO NOT YET LOOK FOR CUMULATIVE VALUES
    def test_cumulative(self):
        sent = 'In total nationwide, 613 cases of the disease have been reported as of 2 July 2014, with 63 deceased patients'
        counts = [
            {'count': 613, 'attributes': ['infection', 'cumulative']},
            {'count': 63, 'attributes': ['infection', 'death']}
        ]
        self.assertHasCounts(sent, counts)

    def test_cumulative_2(self):
        sent = 'it has already claimed about 455 lives in Guinea'
        counts = [
            {
                'count': 455,
                'attributes': ['approximate', 'infection', 'cumulative', 'death']}
        ]
        self.assertHasCounts(sent, counts)

    # TODO: Support the 'suspected' attribute. Look through additional attributes.
    def test_attributes(self):
        self.assertHasCounts('There have been 12 reported cases in Colorado. '
                             'There was one suspected case of bird flu in the country.',
                             [{'count': 12, 'attributes': ['infection']},
                              {'count': 1, 'attributes': ['infection', 'suspected']}])

    def test_attributes_2(self):
        self.assertHasCounts('The average number of cases reported annually is 600',
                             [{'count': 600, 'attributes': ['annual', 'average', 'infection']}])

    def test_attributes_3(self):
        self.assertHasCounts("""
As of [Thu 7 Sep 2017], there have been a total of:
1715 laboratory-confirmed cases of MERS-CoV infection, including
690 deaths [reported case fatality rate 40.2 percent],
1003 recoveries, and 0 currently active cases/infections
        """, [
            {'count': 1715, 'attributes': ['infection', 'confirmed', 'cumulative']},
            {'count': 690, 'attributes': ['infection', 'death']},
            {'count': 1003, 'attributes': ['infection', 'recovery']},
            {'count': 0, 'attributes': ['infection', 'ongoing']}
        ])

    def test_misc(self):
        sent = """How many cases occured with 3.2 miles of Katanga Province?
                  Three fatalities have been reported."""
        counts = [
            {
                'count': 3,
                'attributes': ['death']}
        ]
        self.assertHasCounts(sent, counts)

# I'm pretty sure this one is off just because we look for very different things, and I didn't rewrite it with the new expected values.
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
                         for count in doc.tiers['infections'].spans
                         if 'infection' in count.metadata['attributes']]
        self.assertSequenceEqual(actual_counts, expected_counts)

# There's no way we'd find this yet. If we want to, we should write a separate module or function to search for this syntactical structure.
    def test_singular_cases_4(self):
        self.assertHasCounts('the cases include a 27-year-old woman and 2 males, each of 37 years',
                             [{'count': 1}, {'count': 2}])

# TODO: Implement ranges
    def test_ranges(self):
        self.assertHasCounts('10 to 13 suspected cases of Ebola.', [
            {
                'count': 10,
                'attributes': ['infection', 'min', 'suspected']
            }, {
                'count': 13,
                'attributes': ['infection', 'max', 'suspected']
            }
        ])

    # # We don't look for incremental counts right now
    def test_attribute_fp(self):
        # Make sure the count is not parsed as incremental becasue of the
        # new in New York.
        self.assertHasCounts('5 cases of Dengue in New York.', [
            {'count': 5, 'attributes': ['infection']}])


if __name__ == '__main__':
    unittest.main()
