#!/usr/bin/env python
"""Named entity annotator"""
from annotator import Annotator, AnnoSpan, AnnoTier
from spacy_annotator import SpacyAnnotator
class NEAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.nes' not in doc.tiers:
            doc.add_tier(SpacyAnnotator())
        doc.tiers['nes'] = doc.tiers['spacy.nes']
        return doc
