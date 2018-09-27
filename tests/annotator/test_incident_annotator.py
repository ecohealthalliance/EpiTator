#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest
from . import test_utils
from epitator.annotator import AnnoDoc
from epitator.count_annotator import CountAnnotator
from epitator.infection_annotator import InfectionAnnotator
from epitator.incident_annotator import IncidentAnnotator
from six.moves import zip


class TestIncidentAnnotator(unittest.TestCase):

    def setUp(self):
        self.annotator = IncidentAnnotator()

    def test_verb_counts(self):
        doc = AnnoDoc('It brings the number of cases reported to 28 in Jeddah since 27 March 2014')
        doc.add_tier(self.annotator)

    def test_alternate_case_counts(self):
        doc = AnnoDoc('These 2 new cases bring to 4 the number stricken in California in 2012.')
        case_counts = doc.require_tiers('infections', via=InfectionAnnotator)
        attribute_remappings = {
            'infection': 'case'
        }
        for span in case_counts:
            span.metadata['attributes'] = [
                attribute_remappings.get(attribute, attribute)
                for attribute in span.metadata['attributes']]
        doc.add_tier(self.annotator, case_counts=case_counts)
