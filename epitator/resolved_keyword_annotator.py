#!/usr/bin/env python
"""Annotates keywords from the synonyms database
and resolves them to uris."""
from __future__ import absolute_import
from collections import defaultdict
from .annotator import Annotator, AnnoSpan, AnnoTier
from .ngram_annotator import NgramAnnotator
from .get_database_connection import get_database_connection
import sqlite3
import logging


logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class ResolvedKeywordSpan(AnnoSpan):
    def __init__(self, span, resolutions):
        super(ResolvedKeywordSpan, self).__init__(
            span.start,
            span.end,
            span.doc,
            metadata={
                'resolutions': resolutions
            })
        self.resolutions = resolutions

    def __repr__(self):
        ids = [r['entity_id'] for r in self.resolutions]
        return super(ResolvedKeywordSpan, self).__repr__() + str(ids)

    def to_dict(self):
        result = super(ResolvedKeywordSpan, self).to_dict()
        result['resolutions'] = []
        for res in self.resolutions:
            res_dict = {k: res[k] for k in res.keys()}
            entity = res['entity']
            res_dict['entity'] = {k: entity[k] for k in entity.keys()}
            result['resolutions'].append(res_dict)
        return result


class ResolvedKeywordAnnotator(Annotator):
    def __init__(self):
        self.connection = get_database_connection()
        self.connection.row_factory = sqlite3.Row

    @property
    def synonyms(self):
        cursor = self.connection.cursor()
        return cursor.execute("""
        SELECT * FROM synonyms ORDER BY synonym""")

    def annotate(self, doc):
        logger.info('start resolved keyword annotator')
        if 'ngrams' not in doc.tiers:
            doc.add_tiers(NgramAnnotator())
            logger.info('%s ngrams' % len(doc.tiers['ngrams']))
        span_text_to_spans = defaultdict(list)
        for ngram_span in doc.tiers['ngrams'].spans:
            span_text = ngram_span.text
            span_text_to_spans[ngram_span.text].append(ngram_span)
            if span_text != span_text.lower():
                span_text_to_spans[span_text.lower()].append(ngram_span)

        ngrams = list(set(span_text_to_spans.keys()))
        cursor = self.connection.cursor()

        spans_to_resolved_keywords = defaultdict(list)
        entity_ids = set()
        ordered_ngram_iter = iter(sorted(ngrams))
        try:
            ngram = next(ordered_ngram_iter)
            for result in self.synonyms:
                while ngram < result['synonym']:
                    ngram = next(ordered_ngram_iter)
                if ngram == result['synonym']:
                    # increase the weight of entities matching longer spans of text
                    # as they are less likely to be false positives.
                    if len(ngram) > 12:
                        match_weight = 2
                    elif len(ngram) > 10:
                        match_weight = 1
                    else:
                        match_weight = 0
                    for span in span_text_to_spans[ngram]:
                        spans_to_resolved_keywords[span].append(
                            dict(result,
                                 weight=result['weight'] + match_weight))
                        entity_ids.add(result['entity_id'])
        except StopIteration:
            pass

        logger.info('%s entities resolved' % len(entity_ids))

        results = cursor.execute('''
             SELECT id, label, type
             FROM entities
             WHERE id IN (''' + ','.join('?' for x in entity_ids) + ')', list(entity_ids))
        ids_to_entities = {}
        for result in results:
            ids_to_entities[result['id']] = result
        spans = []
        for span, resolved_keywords in spans_to_resolved_keywords.items():
            sorted_resolved_keywords = sorted(resolved_keywords,
                                              key=lambda k: -k['weight'])
            resolutions = []
            span_entitiy_ids = set()
            for keyword in sorted_resolved_keywords:
                if keyword['entity_id'] in span_entitiy_ids:
                    continue
                span_entitiy_ids.add(keyword['entity_id'])
                res_dict = {'entity_id': keyword['entity_id'],
                            'entity': ids_to_entities[keyword['entity_id']],
                            'weight': keyword['weight']}
                resolutions.append(res_dict)
            spans.append(ResolvedKeywordSpan(span, resolutions))
        tier = AnnoTier(spans).optimal_span_set()
        return {'resolved_keywords': tier}
