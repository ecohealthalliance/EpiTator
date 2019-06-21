#!/usr/bin/env python
"""
Tests our ability to annotate sentences with numerical
instances of infections, hospitalizations and deaths.
"""
from __future__ import absolute_import
import unittest
from epitator.database_interface import DatabaseInterface


class TestCountAnnotator(unittest.TestCase):

    def setUp(self):
        self.db_interface = DatabaseInterface()

    def test_lookup_synonym(self):
        results = self.db_interface.lookup_synonym('foot and mouth', 'disease')
        self.assertEqual([{'synonym': u'hand, foot and mouth disease',
                           'id': u'http://purl.obolibrary.org/obo/DOID_10881',
                           'weight': 3,
                           'label': u'hand, foot and mouth disease'}], list(results))

    def test_lookup_synonym2(self):
        results = self.db_interface.lookup_synonym('Creutzfeldt - Jakob', 'disease')
        self.assertEqual('Creutzfeldt-Jakob disease', next(results)['label'])

    def test_lookup_synonym3(self):
        results = self.db_interface.lookup_synonym('Tick Borne Encephalitis', 'disease')
        self.assertEqual('http://purl.obolibrary.org/obo/DOID_0050175', next(results)['id'])

    def test_get_entity(self):
        result = self.db_interface.get_entity('http://purl.obolibrary.org/obo/DOID_4325')
        self.assertEqual({'source': u'Disease Ontology',
                          'type': u'disease',
                          'id': u'http://purl.obolibrary.org/obo/DOID_4325',
                          'label': u'Ebola hemorrhagic fever'}, result)
