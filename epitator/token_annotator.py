#!/usr/bin/env python
"""Token Annotator"""
from __future__ import absolute_import
from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator


class TokenAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        doc.tiers['tokens'] = doc.tiers['spacy.tokens']
        return doc
