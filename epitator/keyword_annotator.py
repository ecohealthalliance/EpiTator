#!/usr/bin/env python
"""Keyword Annotator"""
from __future__ import absolute_import
from collections import defaultdict
from .annotator import Annotator, AnnoTier, AnnoSpan
from .ngram_annotator import NgramAnnotator
import os
import pickle
import six


class KeywordAnnotator(Annotator):

    keyword_types = ['diseases', 'hosts', 'modes', 'pathogens', 'symptoms']

    keyword_type_map = {
        'doid/diseases': 'diseases',
        'eha/disease': 'diseases',
        'pm/disease': 'diseases',
        'hm/disease': 'diseases',
        'biocaster/diseases': 'diseases',
        'eha/symptom': 'symptoms',
        'biocaster/symptoms': 'symptoms',
        'doid/has_symptom': 'symptoms',
        'pm/symptom': 'symptoms',
        'symp/symptoms': 'symptoms',
        'wordnet/hosts': 'hosts',
        'eha/vector': 'hosts',
        'wordnet/pathogens': 'pathogens',
        'biocaster/pathogens': 'pathogens',
        'pm/mode of transmission': 'modes',
        'doid/transmitted_by': 'modes',
        'eha/mode of transmission': 'modes'
    }

    def __init__(self, db=None):
        with open(os.environ.get('KEYWORD_PICKLE_PATH') or 'current_classifier/keyword_array.p', 'rb') as f:
            args = dict()
            if six.PY3:
                args = dict(fix_imports=True)
            keyword_array = pickle.load(f, **args)
        self.keywords = defaultdict(dict)
        for keyword in keyword_array:
            if keyword['category'] in self.keyword_type_map:
                keyword_type = self.keyword_type_map[keyword['category']]
                self.keywords[keyword_type][keyword['keyword'].lower()] = [
                    keyword['keyword'], keyword['case_sensitive']]

    def annotate(self, doc):

        if 'ngrams' not in doc.tiers:
            doc.add_tiers(NgramAnnotator())

        ngram_spans_by_lowercase = defaultdict(list)

        for ngram_span in doc.tiers['ngrams'].spans:
            ngram_spans_by_lowercase[ngram_span.text.lower()].append(
                ngram_span)

        ngrams = list(ngram_spans_by_lowercase.keys())

        for keyword_type, keywords in self.keywords.items():

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
                        keyword_spans.append(
                            AnnoSpan(ngram_span.start, ngram_span.end, doc, label=label))

            doc.tiers[keyword_type] = AnnoTier(keyword_spans).optimal_span_set()

        return doc
