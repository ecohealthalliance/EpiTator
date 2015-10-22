#!/usr/bin/env python
# coding=utf8
import sys
import unittest
import test_utils

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.case_count_annotator import CaseCountAnnotator

class OldCaseCountAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = CaseCountAnnotator()

    def test_slow_article(self):
        """
        This document is a test case because of a pattern bug that causes it
        to take an extremely long time to parse as is.
        https://github.com/clips/pattern/issues/104
        """
        doc = AnnoDoc(u"2012 — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — the coordination of Epidemiological surveillance,")
        doc.add_tier(self.annotator)
    
    def test_buggy_article(self):
        """
        The hypen was triggering an exception:
        https://github.com/ecohealthalliance/annie/issues/31
        """
        doc = AnnoDoc("The authors say that a complex combination of factors—such as virus mutation")
        doc.add_tier(self.annotator)
