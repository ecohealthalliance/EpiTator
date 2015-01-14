#!/usr/bin/env python
# coding=utf8
import sys
import unittest
import test_utils
sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.patient_info_annotator import PatientInfoAnnotator
from annotator.case_count_annotator import CaseCountAnnotator

class PatternBugTests(unittest.TestCase):

    def setUp(self):
        self.annotator = PatientInfoAnnotator()

    def test_parse_emoticon(self):
        # Pattern parses ": 3" as a single word, I think because it thinks it is
        # an emoticon. However doing so removes the space which can cause
        # bugs.
        doc = AnnoDoc("""
        Number of new cases: 3
        """)
        doc.add_tier(self.annotator)

    def test_match_long_ellipsis2(self):
        doc = AnnoDoc(u"""They will also be used to give the all-clear for Ebola patients who survive the disease...""")
        doc.add_tier(self.annotator)

    def test_end(self):
        doc = AnnoDoc(u"n ��i.\n \n")
        doc.add_tier(CaseCountAnnotator())

if __name__ == '__main__':
    unittest.main()
