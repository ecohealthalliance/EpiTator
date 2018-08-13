#!/usr/bin/env python
"""Ngram Annotator"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier, AnnoSpan
from .token_annotator import TokenAnnotator
from six.moves import range


class NgramAnnotator(Annotator):

    def __init__(self, n_min=1, n_max=5):
        self.n_min = n_min
        self.n_max = n_max

    def annotate(self, doc):

        if 'tokens' not in doc.tiers:
            doc.add_tiers(TokenAnnotator())

        ngram_spans = []

        token_spans = doc.tiers['tokens'].spans

        for n in range(self.n_min, self.n_max + 1):
            for i in range(len(token_spans)):
                if i + n > len(token_spans):
                    break
                span = AnnoSpan(token_spans[i].start,
                                token_spans[i + n - 1].end,
                                doc)
                ngram_spans.append(span)

        doc.tiers['ngrams'] = AnnoTier(ngram_spans)

        return doc
