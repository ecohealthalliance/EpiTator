#!/usr/bin/env python
"""Part of speech tag annotator"""

import nltk

from annotator import *
from token_annotator import TokenAnnotator

class POSAnnotator(Annotator):

    def __init__(self, tag=nltk.pos_tag):
        """tagger should be a function that takes a list of strings and returns
           a list of tuples(token: str, pos: str)"""
        self.tag = tag

    def annotate(self, doc):

        if not 'tokens' in doc.tiers:
            token_annotator = TokenAnnotator()
            doc.add_tier(token_annotator)

        pos_tags = self.tag(doc.tiers['tokens'].labels())

        pos_spans = [AnnoSpan(span.start, span.end, doc, label=tag[1])
                     for tag, span in zip(pos_tags, doc.tiers['tokens'].spans)]

        doc.tiers['pos'] = AnnoTier(pos_spans)

        return doc
