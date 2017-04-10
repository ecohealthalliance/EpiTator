    #!/usr/bin/env python
"""Keyword Annotator"""
import re
from collections import defaultdict
from annotator import *
from ngram_annotator import NgramAnnotator
from get_database_connection import get_database_connection
import sqlite3
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

class ResolvedKeywordSpan(AnnoSpan):
    def __init__(self, span, resolved_keywords, uris_to_labels):
        self.__dict__ = dict(span.__dict__)
        self.resolutions = []
        self.uris = []
        for keyword in sorted(resolved_keywords, key=lambda k: k['weight']):
            if keyword['uri'] not in self.uris:
                self.uris.append(keyword['uri'])
                self.resolutions.append(dict(
                    uri=keyword['uri'],
                    weight=keyword['weight'],
                    label=uris_to_labels[keyword['uri']]))
    def __repr__(self):
        return super(ResolvedKeywordSpan, self).__repr__() + str(self.uris)
    def to_dict(self):
        result = super(ResolvedKeywordSpan, self).to_dict()
        result['resolutions'] = list(self.resolutions)
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
            logger.info('ngrams')
        span_text_to_spans = defaultdict(list)
        for ngram_span in doc.tiers['ngrams'].spans:
            span_text = ngram_span.text
            span_text_to_spans[ngram_span.text].append(ngram_span)
            if span_text != span_text.lower():
                span_text_to_spans[span_text.lower()].append(ngram_span)

        ngrams = list(set(span_text_to_spans.keys()))
        cursor = self.connection.cursor()

        spans_to_resolved_keywords = defaultdict(list)
        uris = set()
        ordered_ngram_iter = iter(sorted(ngrams))
        try:
            ngram = next(ordered_ngram_iter)
            for result in cursor.execute('SELECT * FROM synonyms ORDER BY synonym'):
                while ngram < result['synonym']:
                    ngram = next(ordered_ngram_iter)
                if ngram == result['synonym']:
                    for span in span_text_to_spans[ngram]:
                        spans_to_resolved_keywords[span].append(result)
                        uris.add(result['uri'])
        except StopIteration:
            pass

        logger.info('%s uris resolved' % len(uris))

        results  = cursor.execute('''
        SELECT *
        FROM entity_labels
        WHERE uri IN (''' +
        ','.join('?' for x in uris) +
        ')', list(uris))
        uris_to_labels = defaultdict(list)
        for result in results:
            uris_to_labels[result['uri']].append(result['label'])

        doc.tiers['resolved_keywords'] = AnnoTier([
            ResolvedKeywordSpan(span, resolved_keywords, uris_to_labels)
            for span, resolved_keywords in spans_to_resolved_keywords.items()])
        doc.tiers['resolved_keywords'].filter_overlapping_spans()
        doc.tiers['resolved_keywords'].sort_spans()

        return doc
