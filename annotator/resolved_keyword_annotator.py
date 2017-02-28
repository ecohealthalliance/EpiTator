    #!/usr/bin/env python
"""Keyword Annotator"""
import re
from collections import defaultdict
from annotator import *
from ngram_annotator import NgramAnnotator
from get_database_connection import get_database_connection
import sqlite3

class ResolvedKeywordSpan(AnnoSpan):
    def __init__(self, span, resolved_keywords):
        self.__dict__ = dict(span.__dict__)
        self.uris = []
        for keyword in sorted(resolved_keywords, key=lambda k: k['weight']):
            if keyword['uri'] not in self.uris:
                self.uris.append(keyword['uri'])
    def __repr__(self):
        return super(ResolvedKeywordSpan, self).__repr__() + str(self.uris)
    def to_dict(self):
        result = super(ResolvedKeywordSpan, self).to_dict()
        result['uris'] = list(self.uris)
        return result

class ResolvedKeywordAnnotator(Annotator):
    def __init__(self):
        self.connection = get_database_connection()
        self.connection.row_factory = sqlite3.Row

    def annotate(self, doc):
        if 'ngrams' not in doc.tiers:
            ngram_annotator = NgramAnnotator()
            doc.add_tier(ngram_annotator)

        span_text_to_spans = defaultdict(list)
        for ngram_span in doc.tiers['ngrams'].spans:
            span_text = ngram_span.text
            span_text_to_spans[ngram_span.text].append(ngram_span)
            if span_text != span_text.lower():
                span_text_to_spans[span_text.lower()].append(ngram_span)

        ngrams = list(set(span_text_to_spans.keys()))
        cursor = self.connection.cursor()
        results  = cursor.execute('''
        SELECT *
        FROM synonyms
        WHERE synonym IN (''' +
        ','.join('?' for x in ngrams) +
        ')', ngrams)

        spans_to_resolved_keywords = defaultdict(list)
        for result in results:
            for span in span_text_to_spans[result['synonym']]:
                spans_to_resolved_keywords[span].append(result)

        doc.tiers['resolved_keywords'] = AnnoTier([
            ResolvedKeywordSpan(span, resolved_keywords)
            for span, resolved_keywords in spans_to_resolved_keywords.items()])
        doc.tiers['resolved_keywords'].filter_overlapping_spans()
        doc.tiers['resolved_keywords'].sort_spans()

        return doc
