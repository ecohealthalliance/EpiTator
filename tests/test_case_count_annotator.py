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
        examples = [
            ("it brings the number of cases reported in Jeddah since 27 Mar 2014 to 28", 28),
            ("The number of cases exceeds 30", 30)]

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

    def test_written_numbers(self):
        self.doc.text = "two hundred and twenty two patients were admitted to hospitals"
        self.doc.add_tier(self.annotator)
        print "self.doc.tiers['caseCounts']", self.doc.tiers['caseCounts']
        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 26)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 222)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'hospitalizationCount')

    def test_death_counts(self):

        self.doc.text = "Nine patients died last week"
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 0)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 4)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 9)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'deathCount')

    def test_death_counts_pattern_problem(self):

        self.doc.text = "Deaths : 2"
        # TODO -- should this work with self.doc.text = "Deaths : 2" ?
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 1)
        # TODO -- why does this start at 0?
        # self.assertEqual(self.doc.tiers['caseCounts'].spans[0].start, 8)
        # self.assertEqual(self.doc.tiers['caseCounts'].spans[0].end, 9)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'deathCount')

    def test_misc(self):
        self.doc.text = "1200 children between the ages of 2-5 are afflicted with a mystery illness"
        self.doc.add_tier(self.annotator)
        
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].type, 'caseCount')
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 1200)

    def test_misc2(self):
        self.doc.text = "These 2 new cases bring to 4 the number of people stricken in California this year [2012]."
        self.doc.add_tier(self.annotator)

        self.assertEqual(len(self.doc.tiers['caseCounts']), 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 4)
        
    def test_duplicates(self):
        self.doc.text = "Two patients died out of four patients."
        self.doc.add_tier(self.annotator)
        
        self.assertEqual(len(self.doc.tiers['caseCounts']), 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[0].label, 2)
        self.assertEqual(self.doc.tiers['caseCounts'].spans[1].label, 4)

if __name__ == '__main__':
    unittest.main()