    #!/usr/bin/env python
"""Keyword Annotator"""
import math
import re
from collections import defaultdict

from pymongo import MongoClient
import os

from annotator import *
from ngram_annotator import NgramAnnotator

class KeywordAnnotator(Annotator):

    keyword_types = ['diseases', 'hosts', 'modes', 'pathogens', 'symptoms']

    def __init__(self, db=None):
        if not db:
            if 'MONGO_URL' in os.environ:
                mongo_url = os.environ['MONGO_URL']
            else:
                mongo_url = 'mongodb://localhost:27017'

            client = MongoClient(mongo_url)
            db = client.annotation

        self.keywords = {}

        for keyword_type in self.keyword_types:
            self.keywords[keyword_type] = {
                res['_id'].lower(): (res['_id'], res['case_sensitive'])
                for res in db[keyword_type].find()
            }

    def annotate(self, doc):

        if 'ngrams' not in doc.tiers:
            ngram_annotator = NgramAnnotator()
            doc.add_tier(ngram_annotator)

        ngram_spans_by_lowercase = defaultdict(list)

        for ngram_span in doc.tiers['ngrams'].spans:
            ngram_spans_by_lowercase[ngram_span.text.lower()].append(ngram_span)

        ngrams = ngram_spans_by_lowercase.keys()

        for keyword_type, keywords in self.keywords.iteritems():

            keyword_spans = []
            for keyword in set(keywords.keys()).intersection(ngrams):
                true_case = keywords[keyword][0]
                case_sensitive = keywords[keyword][1]
                for ngram_span in ngram_spans_by_lowercase[keyword]:
                    if not case_sensitive or ngram_span.text == true_case:
                        if case_sensitive:
                            label = true_case
                        else:
                            label = keyword
                        keyword_spans.append(AnnoSpan(ngram_span.start, ngram_span.end, doc, label=label))

            doc.tiers[keyword_type] = AnnoTier(keyword_spans)
            doc.tiers[keyword_type].filter_overlapping_spans()
            doc.tiers[keyword_type].sort_spans()

        return doc


