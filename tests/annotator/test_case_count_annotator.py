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
from annotator.patient_info_annotator import PatientInfoAnnotator

class CaseCountAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = PatientInfoAnnotator()

    def test_verbal_counts(self):
        # TODO -- this example removed because it is long than the 2 intervening
        # optional words we're allowing in this pattern for now. We should find
        # and efficient way to match this example later.
        # ("it brings the number of cases reported in Jeddah since 27 Mar 2014 to 28", 28)
        examples = [("The number of cases exceeds 30", 30)]

        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['patientInfo']), 1)
            test_utils.assertHasProps(
                doc.tiers['patientInfo'].spans[0].metadata, {
                    'count' : {
                        'min': actual_count,
                    }
                }
            )

    def test_strings_and_unicode(self):

        examples = [("The number of cases exceeds 30", 30),
                    (u"The number of cases exceeds 30", 30)]

        for example, actual_count in examples:
            doc = AnnoDoc(example)
            doc.add_tier(self.annotator)
            self.assertEqual(len(doc.tiers['patientInfo']), 1)
            test_utils.assertHasProps(
                doc.tiers['patientInfo'].spans[0].metadata, {
                    'count' : {
                        'min': actual_count
                    }
                }
            )

    def test_offsets(self):

        doc = AnnoDoc("The ministry of health reports seventy five new patients were admitted")
        doc.add_tier(self.annotator)
        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        self.assertEqual(doc.tiers['patientInfo'].spans[0].start, 31)
        self.assertEqual(doc.tiers['patientInfo'].spans[0].end, 56)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 75
                }
            }
        )

    def test_written_numbers(self):

        doc = AnnoDoc("two hundred and twenty two patients were admitted to hospitals")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 222
                }
            }
        )

    def test_hospital_counts1(self):
        example, actual_count = "33 were hospitalized", 33
        doc = AnnoDoc(example)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': actual_count,
                    'hospitalization': True
                }
            }
        )
        self.assertEqual(len(doc.tiers['patientInfo']), 1)
    def test_hospital_counts2(self):
        example, actual_count = "222 were admitted to hospitals with symptoms of diarrhea", 222
        doc = AnnoDoc(example)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': actual_count,
                    'hospitalization': True
                }
            }
        )
        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        
    def test_death_counts(self):
        """We want to make sure that 'death' is the type of the retained
           span here, as it is also a match for a 'caseCount' pattern."""

        doc = AnnoDoc("Nine patients died last week")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 9,
                    'death': True
                }
            }
        )
    def test_death_counts_pattern_problem(self):
        """The issue here is that CLIPS pattern library will tokenize colons
           separately from the preceding word."""

        doc = AnnoDoc("Deaths: 2")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        self.assertEqual(doc.tiers['patientInfo'].spans[0].start, 0)
        self.assertEqual(doc.tiers['patientInfo'].spans[0].end, 9)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 2,
                    'death': True
                }
            }
        )

    # With the combined patient description / caseCount annotator the span of
    # text no longer corresponds to the count.
    # def test_numbers_last_pattern(self):
    #     """Make sure we can get the proper offsets if we have a numeric portion
    #       that comes at the end of the pattern."""

    #     doc = AnnoDoc("The number of cases exceeds 30")
    #     doc.add_tier(self.annotator)

    #     self.assertEqual(len(doc.tiers['patientInfo']), 1)
    #     self.assertEqual(doc.tiers['patientInfo'].spans[0].start, 28)
    #     self.assertEqual(doc.tiers['patientInfo'].spans[0].end, 30)
    #     self.assertEqual(doc.tiers['patientInfo'].spans[0].label, 30)
    #     self.assertEqual(doc.tiers['patientInfo'].spans[0].type, 'caseCount')

    def test_misc(self):
        doc = AnnoDoc("1200 children between the ages of 2 and 5 are afflicted with a mystery illness")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 1200,
                    'case' : True
                },
                'age' : {
                    'range_start': 2,
                    'range_end' : 5
                }
            }
        )

    def test_misc2(self):
        doc = AnnoDoc("These 2 new cases bring to 4 the number stricken in California this year [2012].")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'incremental': True,
                    'number': 2,
                }
            }
        )
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[1].metadata, {
                'count' : {
                    'number': 4,
                }
            }
        )
        self.assertEqual(len(doc.tiers['patientInfo']), 2)

    def test_duplicates(self):
        doc = AnnoDoc("Two patients died out of four patients.")
        doc.add_tier(self.annotator)

        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 2,
                    'death' : True
                }
            }
        )
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[1].metadata, {
                'count' : {
                    'number': 4
                }
            }
        )
        self.assertEqual(len(doc.tiers['patientInfo']), 2)

    def test_cumulative(self):

        doc = AnnoDoc("In total nationwide, 2613 cases of the disease have been reported as of 2 Jul 2014, with 63 deaths")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['patientInfo']), 2)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 2613,
                    'cumulative': True,
                    'case': True
                },
                
            }
        )
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[1].metadata, {
                'count' : {
                    'number': 63,
                    'death': True
                }
            }
        )

    def test_cumulative2(self):

        doc = AnnoDoc("it has already claimed about 455 lives in Guinea")
        doc.add_tier(self.annotator)

        self.assertEqual(len(doc.tiers['patientInfo']), 1)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 455,
                    'death': True,
                    'cumulative': True
                }
            }
        )

    def test_cumulative3(self):

        doc = AnnoDoc("there have been a total of 176 cases of human infection with influenza A(H1N5) virus including 64 deaths in Egypt")
        doc.add_tier(self.annotator)

        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 176,
                    'case': True,
                    'cumulative': True
                }
            }
        )
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[1].metadata, {
                'count' : {
                    'number': 64,
                    'death': True,
                    # I'm not sure if we should infer that the death count is
                    # cumulative when the count is not explicity described as such
                    #'cumulative': True
                }
            }
        )
        self.assertEqual(len(doc.tiers['patientInfo']), 2)
        
    def test_value_modifier(self):
        doc = AnnoDoc("The average number of cases reported annually is 600")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 600,
                    'average': True,
                    'annual' : True,
                    'case' : True
                }
            }
        )
        self.assertFalse(
            doc.tiers['patientInfo'].spans[0].metadata.get('count', {}).get('cumulative')
        )

    def test_adjective_or_verb(self):
        """Sometimes the parse tree is wrong and identifies adjectives as verbs,
           so check to make sure our patterns are coping with that."""

        doc = AnnoDoc("There have been 12 reported cases in Colorado. There was one suspected case of bird flu in the country.")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 12,
                    'case': True
                }
            }
        )
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[1].metadata, {
                'count' : {
                    'number': 1,
                }
            }
        )
    def test_hyphenated_numbers(self):

        doc = AnnoDoc("There have been nine hundred ninety-nine reported cases.")
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(
            doc.tiers['patientInfo'].spans[0].metadata, {
                'count' : {
                    'number': 999,
                }
            }
        )


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

"""
