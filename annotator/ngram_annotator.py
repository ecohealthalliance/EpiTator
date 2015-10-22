#!/usr/bin/env python
"""Ngram Annotator"""

from annotator import *
from token_annotator import TokenAnnotator

class NgramAnnotator(Annotator):

    def __init__(self, tokenizer=None):
        pass


    def annotate(self, doc, n_min=1, n_max=7):

        if not 'tokens' in doc.tiers:
            token_annotator = TokenAnnotator()
            doc.add_tier(token_annotator)

        doc.tiers['ngrams'] = AnnoTier()
        for n in range(n_min, n_max + 1):
            doc.tiers[str(n) + 'grams'] = AnnoTier()

        token_spans = doc.tiers['tokens'].spans

        for n in range(n_min, n_max + 1):
            for i in range(len(token_spans)):
                if i + n > len(token_spans):
                    break
                span = AnnoSpan(token_spans[i].start,
                                token_spans[i + n - 1].end,
                                doc)
                doc.tiers['ngrams'].spans.append(span)
                doc.tiers[str(n) + 'grams'].spans.append(span)

        # Remove any ngram tiers for which there are no ngrams
        for n in range(n_min, n_max + 1):
            if len(doc.tiers[str(n) + 'grams'].spans) == 0:
                del(doc.tiers[str(n) + 'grams'])

        return doc
