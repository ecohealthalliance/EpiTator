#!/usr/bin/env python
"""Named entity annotator"""

import nltk

from annotator import *
from pos_annotator import POSAnnotator

class NEAnnotator(Annotator):

    def __init__(self, tag=nltk.ne_chunk):
        """tagger should be a function that takes a list of strings and returns
           a list of tuples(token: str, pos: str)"""
        self.tag = tag

    def annotate(self, doc):

        if not 'pos' in doc.tiers:
            pos_annotator = POSAnnotator()
            doc.add_tier(pos_annotator)

        ne_tags = self.tag(zip(doc.tiers['tokens'].labels(), doc.tiers['pos'].labels()))

        ne_spans = []

        span_id = 0
        token_spans = doc.tiers['pos'].spans
        for tag in ne_tags:
            if type(tag) is nltk.tree.Tree:
                ne_spans.append(AnnoSpan(token_spans[span_id].start,
                                     token_spans[span_id + len(tag.leaves()) - 1].end,
                                     doc,
                                     label=tag.node))
                span_id += len(tag.leaves())
            else:
                span_id += 1

        doc.tiers['nes'] = AnnoTier(ne_spans)
        print "add nes:", doc.tiers['nes']

        return doc



