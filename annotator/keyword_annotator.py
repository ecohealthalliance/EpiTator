#!/usr/bin/env python
"""Keyword Annotator"""
import math
import re
from collections import defaultdict

import pymongo

from annotator import *
from ngram_annotator import NgramAnnotator

class KeywordAnnotator(Annotator):

    keyword_types = ['diseases', 'hosts', 'modes', 'pathogens', 'symptoms']

    def __init__(self, db=None):
        if not db:
            db = pymongo.Connection('localhost', port=27017)['annotation']

        self.keywords = {}

        for keyword_type in self.keyword_types:
            self.keywords[keyword_type] = set( [ res['_id'] for res in db[keyword_type].find() ] )

    def annotate(self, doc):

        if 'ngrams' not in doc.tiers:
            ngram_annotator = NgramAnnotator()
            doc.add_tier(ngram_annotator)

        ngram_spans_by_lowercase = defaultdict(list)

        for ngram_span in doc.tiers['ngrams'].spans:
            ngram_spans_by_lowercase[ngram_span.text.lower()].append(ngram_span)
        lowercase_ngrams = ngram_spans_by_lowercase.keys()

        for keyword_type, keywords in self.keywords.iteritems():
            keyword_spans = []
            for keyword in keywords.intersection(lowercase_ngrams):
                for ngram_span in ngram_spans_by_lowercase[keyword]:
                    keyword_spans.append(AnnoSpan(ngram_span.start, ngram_span.end, doc, label=keyword))
            doc.tiers[keyword_type] = AnnoTier(keyword_spans)
            doc.tiers[keyword_type].filter_overlapping_spans()
            doc.tiers[keyword_type].sort_spans()

        return doc


