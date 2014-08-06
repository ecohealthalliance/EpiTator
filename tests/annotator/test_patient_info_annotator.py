#!/usr/bin/env python
import sys
import unittest
import test_utils
sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.patient_info_annotator import PatientInfoAnnotator

class PatientInfoAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = PatientInfoAnnotator()

    def test_snippit1(self):
        # based on: http://www.promedmail.org/direct.php?id=2638359
        # Hyphenated words are a problem that has not been addressed yet.
        # Phrases like 10-year-old are treated as single words by pattern
        # which makes it so we can't search for them.
        # Numeric ranges separated by a hyphen (e.g. 1-14) also get treated
        # as an individual entity, and to make matters more complicated, 
        # they can be confused with date strings and number like ninety-nine.
        doc = AnnoDoc("""
        A 10 year old girl of Sippi village in Upper Subansiri district,
        who was admitted to Arunachal State Hospital died on Thursday,
        state epidemiologist Dr L Jampa told PTI on Saturday [26 Jul 2014].
        The other affected people include children in the age group of
        approximately 1 - 14 years besides an 18 year old, he stated.
        They were undergoing treatment at the Arunachal State Hospital [ASH]
        since last week, while approximately 12 cases being treated in Guwahati
        Medical College Hospital in Assam were reportedly improving, he said.
        """)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[0].metadata, {
            'age' : {
                'number': 10,
                'year_units': True,
            },
            'female': True
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[1].metadata, {
            'age' : {
                'child': True,
            }
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[2].metadata, {
            'age' : {
                'range_start': 1,
                'range_end': 14,
                'approximate': True,
                'year_units': True
            }
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[3].metadata, {
            'age' : {
                'number': 18,
                'year_units': True
            }
        })
    
    def test_snippit2(self):
        # based on: http://www.promedmail.org/direct.php?id=2641341
        doc = AnnoDoc("""
        If the person has a positive history of previous infection with Q fever,
        vaccination is contraindicated; in others, serum antibody determination
        and skin tests must be done before vaccination to exclude those
        likely to have severe local or systemic hypersensitivity reactions to
        the vaccine resulting from previous unrecognized exposure to the organism
        (http://www.immunise.health.gov.au/internet/immunise/publishing.nsf/Content/handbook10-4-15).
        Q fever vaccine is not routinely recommended for children aged less than
        15 years of age and pregnant or breastfeeding women because safety of
        the vaccine in these situations has not been established.
        Revaccination is not indicated due to the possibility of severe
        hypersensitivity reactions.
        """)
        doc.add_tier(self.annotator)
        # This should probably be folded into the other match somehow
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[0].metadata, {
            'age' : {
                'child': True
            }
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[1].metadata, {
            'female': True,
            'age' : {
                'max': 15,
                'year_units': True
            }
        })
        
    def test_senior(self):
        # based on: http://www.promedmail.org/direct.php?id=2070771
        doc = AnnoDoc("""
        The senior physician of the Chelyabinsk Region organised immunisation of
        all medical workers, teachers, and school employees under the age of 35.
        According to officials, 58 cases of measles had been confirmed so far.
        """)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[0].metadata, {
            'age' : {
                'max': 35
            }
        })

    def test_key_cat(self):
        # based on: http://www.promedmail.org/direct.php?id=2499795
        doc = AnnoDoc("""
        Details of the cases are as follows:
        - A 71 year old male farmer from Meizhou City, Guandong Province.
        He had onset of symptoms on [10 May 2014],
        was admitted to a hospital on [12 May 2014],
        and is currently in a mild condition.
        He had a history of exposure to live poultry.
        """)
        doc.add_tier(self.annotator, keyword_categories={
            'occupation' : [
                'farmer',
                'hosptial worker'
            ]
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[0].metadata, {
            'age' : {
                'number': 71,
            },
            'male': True,
            'occupation': u'farmer'
        })
