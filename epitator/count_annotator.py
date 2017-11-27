#!/usr/bin/env python
"""
Annotates counts with the following attributes:
cumulative, case, death, age, hospitalization, approximate, min, max
"""
from __future__ import absolute_import
import re
from .annotator import Annotator, AnnoTier, AnnoSpan
from .annospan import SpanGroup
from .spacy_annotator import SpacyAnnotator
from .date_annotator import DateAnnotator
from . import result_aggregators as ra
from . import utils
from .spacy_nlp import spacy_nlp
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

in_case_token = spacy_nlp(u"Break glass in case of emergency.")[3]


class CountSpan(AnnoSpan):
    def __init__(self, span, metadata):
        self.start = span.start
        self.end = span.end
        self.doc = span.doc
        self.label = span.text
        self.metadata = metadata

    def to_dict(self):
        result = super(CountSpan, self).to_dict()
        result.update(self.metadata)
        result['text'] = self.text
        return result


def is_valid_count(count_string):
    """
    Cull the false-positive counts
    Remove counts that have fractional values, begin with 0
    or are extremely large
    """
    value = utils.parse_spelled_number(count_string)
    if count_string[0] == '0' and len(count_string) > 1:
        return False
    try:
        if int(value) != value:
            return False
    except (TypeError, ValueError) as e:
        logger.info('Cannot parse count string: ' + count_string)
        logger.info(str(e))
        return False
    if value > 1000000000:
        return False
    return True


def search_spans_for_regex(regex_term, spans, match_name=None):
    regex = re.compile(r'^' + regex_term + r'$', re.I)
    match_spans = []
    for span in spans:
        if regex.match(span.text):
            match_spans.append(span)
    return match_spans


class CountAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        if 'dates' not in doc.tiers:
            doc.add_tiers(DateAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']
        counts = []
        for ne_span in spacy_nes:
            if ne_span.label in ['QUANTITY', 'CARDINAL']:
                if is_valid_count(ne_span.text):
                    counts.append(SpanGroup([ne_span], 'count'))
                else:
                    joiner_offsets = [m.span()
                                      for m in re.finditer(r'\s(?:to|and|or)\s',
                                                           ne_span.text)]
                    if len(joiner_offsets) == 1:
                        range_start = AnnoSpan(ne_span.start, ne_span.start + joiner_offsets[0][0], doc)
                        range_end = AnnoSpan(ne_span.start + joiner_offsets[0][1], ne_span.end, doc)
                        if is_valid_count(range_start.text):
                            counts.append(SpanGroup([range_start], 'count'))
                        if is_valid_count(range_end.text):
                            counts.append(SpanGroup([range_end], 'count'))

        def search_regex(regex_term, match_name=None):
            return ra.label(match_name, search_spans_for_regex(
                regex_term, spacy_tokens.spans))

        spacy_lemmas = [span.token.lemma_ for span in spacy_tokens]

        def search_lemmas(lemmas, match_name=None):
            match_spans = []
            lemmas = set(lemmas)
            for span, lemma in zip(spacy_tokens, spacy_lemmas):
                if lemma in lemmas:
                    match_spans.append(span)
            return AnnoTier(ra.label(match_name, match_spans))

        # Add purely numeric counts that were not picked up by the NER.
        counts += AnnoTier(search_regex(r'[1-9]\d{0,6}', 'count')
                           ).without_overlaps(spacy_nes).spans
        # Add count ranges
        ranges = ra.follows([counts,
                             ra.label('range',
                                      ra.follows([search_regex(r'to|and|or'),
                                                  counts]))])
        counts_tier = AnnoTier(ranges + counts).optimal_span_set()
        # Remove counts that overlap an age
        counts_tier = counts_tier.without_overlaps(
            ra.follows([search_regex('age'), search_regex('of'), counts]))
        # Remove distances
        counts_tier = counts_tier.without_overlaps(
            ra.follows([counts, search_regex('kilometers|km|miles|mi')]))
        # Remove counts that overlap a date
        counts_tier = counts_tier.without_overlaps(doc.tiers['dates'])
        modifier_lemma_groups = [
            'average|mean',
            'annual|annually',
            'monthly',
            'weekly',
            'cumulative|total|already',
            'incremental|new|additional|recent',
            'max|less|below|under|most|maximum|up',
            'min|greater|above|over|least|minimum|down|exceeds',
            'approximate|about|near|around',
            'ongoing|active',
        ]
        count_descriptions = AnnoTier(counts_tier)
        person_and_place_nes = spacy_nes.with_label('GPE') + spacy_nes.with_label('PERSON')
        for group in modifier_lemma_groups:
            lemmas = group.split('|')
            results = search_lemmas(lemmas, match_name=lemmas[0])
            # prevent components of NEs like the "New" in New York from being
            # treated as count descriptors.
            results = results.without_overlaps(person_and_place_nes)
            count_descriptions += count_descriptions.with_nearby_spans_from(results)
        case_descriptions = AnnoTier(
            search_lemmas(
                [
                    'death',
                    'die',
                    'kill',
                    'claim',
                    'fatality',
                    'decease'
                ], 'death') +
            search_lemmas(
                [
                    'hospitalization',
                    'hospital',
                    'hospitalize'
                ], 'hospitalization') +
            search_lemmas(['recovery'], 'recovery') +
            search_lemmas(
                [
                    'case',
                    'infect',
                    'infection',
                    'strike'
                ], 'case'))
        case_statuses = (
            search_lemmas(['suspect'], 'suspected') +
            search_lemmas(['confirm'], 'confirmed'))
        case_descriptions += case_descriptions.with_nearby_spans_from(case_statuses, max_dist=1)
        person_descriptions = search_lemmas([
            'man', 'woman',
            'male', 'female',
            'adult', 'senior', 'child',
            'patient',
            'life',
            'person'], 'case')
        case_descriptions += person_descriptions.with_nearby_spans_from(case_descriptions)
        case_descriptions += person_descriptions
        case_descriptions_with_counts = case_descriptions.with_nearby_spans_from(
            count_descriptions,
            max_dist=50)
        # Add singular case reports
        singular_case_spans = []
        determiner_lemmas = set(['a', 'an', 'the', 'one'])
        for cd_span, token_group in case_descriptions.group_spans_by_containing_span(spacy_tokens):
            for t_span in token_group:
                token = t_span.token
                if token.lemma_ == 'case' and token.similarity(in_case_token) < 0.5:
                    continue
                if token.tag_ == 'NN' and any(c.lower_ in determiner_lemmas
                                              for c in token.children):
                    singular_case_spans.append(cd_span)
                    break
        # remove counts that span multiple sentences
        all_potential_counts = (
            case_descriptions_with_counts.spans +
            count_descriptions.spans +
            singular_case_spans)
        single_sentence_counts = []
        for sentence, group in spacy_sentences.group_spans_by_containing_span(all_potential_counts):
            single_sentence_counts += group
        annotated_counts = AnnoTier(single_sentence_counts
                                    ).optimal_span_set(prefer='num_spans_and_no_linebreaks')
        attributes = [
            # count precisions
            'approximate',
            'max',
            'min',
            'average',
            # case status
            'confirmed',
            'suspected',
            # count anchors
            'cumulative',
            'incremental',
            'ongoing',
            # count units
            'case',
            'death',
            'recovery',
            'hospitalization',
            # count periods
            'annual',
            'monthly',
            'weekly',
        ]
        count_spans = []
        for match in annotated_counts:
            match_dict = match.groupdict()
            matching_attributes = set([
                attr for attr in attributes
                if attr in match_dict
            ])
            if set(['death',
                    'hospitalization',
                    'recovery']).intersection(matching_attributes):
                matching_attributes.add('case')
            if 'count' in match_dict:
                count = utils.parse_spelled_number(match_dict['count'][0].text)
            else:
                # For single case reports a count number might not be used.
                # Ex. A new case, the index case
                count = 1
            if 'range' in match_dict:
                lower_count_match = match_dict['count'][0]
                range_match = match_dict['range'][0]
                upper_count_match = range_match.groupdict()['count'][0]
                upper_count = utils.parse_spelled_number(upper_count_match.text)
                count_spans.append(CountSpan(lower_count_match, {
                    'attributes': sorted(list(matching_attributes) + ['min']),
                    'count': count
                }))
                count_spans.append(CountSpan(upper_count_match, {
                    'attributes': sorted(list(matching_attributes) + ['max']),
                    'count': upper_count
                }))
            else:
                count_spans.append(CountSpan(match, {
                    'attributes': sorted(list(matching_attributes)),
                    'count': count
                }))
        return {'counts': AnnoTier(count_spans)}
