#!/usr/bin/env python
"""Named entity annotator"""
from __future__ import absolute_import
from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator


class NEAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.nes' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        doc.tiers['nes'] = doc.tiers['spacy.nes']
        return doc
