#!/usr/bin/env python
"""Annotates keywords from the synonyms database
and resolves them to uris."""
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
from .annospan import SpanGroup
from .ngram_annotator import NgramAnnotator
from .spacy_annotator import SpacyAnnotator
from .get_database_connection import get_database_connection
from collections import defaultdict
import sqlite3
import logging
import re


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
        tokens = doc.require_tiers('spacy.tokens', via=SpacyAnnotator)
        ngrams = doc.require_tiers('ngrams', via=NgramAnnotator)

        span_text_to_spans = defaultdict(list)
        for ngram_span, ngram_tokens in ngrams.group_spans_by_containing_span(tokens):
            span_text = ngram_span.text
            span_text_to_spans[span_text].append(ngram_span)
            # Remove internal hyphens and slashes. Ones at the start and end
            # could be part of punctuation or formatting.
            normalized_text = re.sub(r"\b[\s\-\/]+\b", " ", span_text.lower()).strip()
            if span_text != normalized_text:
                span_text_to_spans[normalized_text].append(ngram_span)
            # Match pluralized keywords by lemmatizing the final token.
            lemmatized_text = ngram_tokens[-1].lemma_
            if not span_text.endswith(lemmatized_text):
                if len(ngram_tokens) > 1:
                    lemmatized_text = SpanGroup(ngram_tokens[0:-1]).text + ' ' + lemmatized_text
                span_text_to_spans[lemmatized_text.lower()].append(ngram_span)

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
            ids_to_entities[result['id']] = {k: result[k] for k in result.keys()}
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
