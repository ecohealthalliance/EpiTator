#!/usr/bin/env python
# coding=utf8
import sys
import unittest
import test_utils
sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.patient_info_annotator import PatientInfoAnnotator

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

    def test_match_long_ellipsis(self):
        """
        Checks for this exception:
        Exception: Cannot match word [\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd] with text [..  \ufffd\ufffd\ufffd\ufffd\ufffd\ufffd]
        """
        # This is a snippit from the article I discovered the exception in.
        # The character encoding turned out not to be related to the bug.
        doc = AnnoDoc(u"""
         ��� ����� ����������, �����-���� �������������� ������������� ����, ��� ������ ��� ���.....  ������ �������...
        """)
        doc.add_tier(self.annotator)
    
    def test_match_long_ellipsis2(self):
        doc = AnnoDoc(u"""They will also be used to give the all-clear for Ebola patients who survive the disease...""")
        doc.add_tier(self.annotator)
        
    def test_line_seperator_char(self):
        """
        These bugs should be resolved in pattern lib.
        https://github.com/clips/pattern/issues/99
        """
        # An empty word is created for the unicode character.
        doc = AnnoDoc(u"""ASIGNAN FONDO CONTINGENTE \u2028 PARA AYUDAR A PRODUCTORES""")
        doc.add_tier(self.annotator)
        # PARA gets doubled in the parse tree.
        # It appears at the end of one sentence and the beginning of another.
        doc = AnnoDoc(u"""ASIGNAN FONDO CONTINGENTE \u2028PARA AYUDAR A PRODUCTORES""")
        doc.add_tier(self.annotator)
        
        
if __name__ == '__main__':
    unittest.main()
