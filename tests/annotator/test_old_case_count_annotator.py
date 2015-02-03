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

    def test_article(self):
        doc = AnnoDoc(u"2012 — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — — the coordination of Epidemiological surveillance,")
        doc.add_tier(self.annotator)
