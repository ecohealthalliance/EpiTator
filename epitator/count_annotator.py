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
from . import result_aggregators as ra
from . import utils
import logging
from functools import reduce
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)
from .spacy_nlp import spacy_nlp

case_count_senses = list(spacy_nlp(u"""
The doctor reviewed the symptoms from the first case of the disease.
In the index case medics recorded a high fever.
For a recent case of Ebola medical attention was not available.
The death of the first patient, a man in his 30s, suprised doctors.
The latest hospitalization involving a febrile disease happend on Monday.
""").sents)
non_case_count_senses = list(spacy_nlp(u"""
The case is spacious container designed to hold many items.
The lawyer's legal case is to be decided in a court of law.
In the case of the first disease action should be taken to prevent it from spreading.
""").sents)

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
        return result


def is_valid_count(count_string):
    """
    Cull the false-positive counts
    Remove counts that have fractional values, begin with 0
    or are extremely large
    """
    value = utils.parse_spelled_number(count_string)
    if count_string[0] == '0':
        return False
    try:
        if int(value) != value:
            return False
    except (TypeError, ValueError) as e:
        logger.info('Cannot parse count string: ' + count_string)
        return False
    if value > 1000000000:
        return False
    return True


def search_spans_for_regex(regex_term, spans, match_name=None):
    regex = re.compile(r'^' + regex_term + r'$', re.I)
    match_spans = []
    for span in spans:
        if regex.match(span.text):
            match_spans.append(SpanGroup([span], match_name))
    return match_spans


class CountAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']
        counts = []
        for ne_span in spacy_nes.spans:
            if ne_span.label in ['QUANTITY', 'CARDINAL'] :
                if is_valid_count(ne_span.text):
                    counts.append(SpanGroup([ne_span], 'count'))
                else:
                    joiner_offsets = [m.span() for m in re.finditer(r'\s(?:to|and|or)\s', ne_span.text)]
                    if len(joiner_offsets) == 1:
                        range_start = AnnoSpan(ne_span.start, ne_span.start + joiner_offsets[0][0], doc)
                        range_end = AnnoSpan(ne_span.start + joiner_offsets[0][1], ne_span.end, doc)
                        if is_valid_count(range_start.text):
                            counts.append(SpanGroup([range_start], 'count'))
                        if is_valid_count(range_end.text):
                            counts.append(SpanGroup([range_end], 'count'))
            elif ne_span.label == 'DATE' and is_valid_count(ne_span.text):
                # Sometimes counts like 1500 are parsed as as the year component
                # of dates. This tries to catch that mistake when the year
                # is long enough ago that it is unlikely to be a date.
                date_as_number = utils.parse_spelled_number(ne_span.text)
                if date_as_number and date_as_number < 1900:
                    counts.append(SpanGroup([ne_span], 'count'))

        def search_regex(regex_term, match_name=None):
            return search_spans_for_regex(
                regex_term, spacy_tokens.spans, match_name)
        # Add count ranges
        ranges = ra.follows([counts,
                             ra.label('range',
                                      ra.follows([search_regex(r'to|and|or'),
                                                  counts]))])
        counts_tier = AnnoTier(ra.combine([ranges, counts]))
        # Remove counts that overlap an age
        counts_tier = counts_tier.without_overlaps(
            ra.follows([search_regex('age'), search_regex('of'), counts]))
        # Remove distances
        counts_tier = counts_tier.without_overlaps(
            ra.follows([counts, search_regex('kilometers|km|miles|mi')]))
        counts = counts_tier.spans
        count_modifiers = ra.combine([
            search_regex('average|mean', 'average') +
            search_regex('annual(ly)?', 'annual') +
            search_regex('monthly', 'monthly') +
            search_regex('weekly', 'weekly') +
            search_regex('total|cumulative|already', 'cumulative') +
            search_regex('(new|additional|recent)(ly)?', 'incremental') +
            search_regex('less|below|under|most|maximum|up', 'max') +
            search_regex('greater|above|over|least|minimum|down|exceeds?', 'min') +
            search_regex('approximate(ly)?|about|near(ly)?|around', 'approximate')])
        count_descriptions = ra.near([count_modifiers, counts]) + counts
        case_descriptions = (
            ra.label('death',
                     search_regex(r'died|killed|claimed|fatalities|fatality|deceased') +
                     search_regex(r'deaths?')) +
            ra.label('hospitalization',
                     # Ex: admitted to hospitals
                     search_regex(r'hospitals?') +
                     search_regex(r'hospitaliz(ations?|ed|es?|ing)')) +
            ra.label('case',
                     search_regex(r'cases?') +
                     search_regex(r'infections?|infect(ed|ing|s)?') +
                     search_regex(r'stricken')))
        case_statuses = (
            search_regex(r'suspect(ed|s|ing)?', 'suspected') +
            search_regex(r'confirmed', 'confirmed'))
        case_descriptions = ra.combine([
            ra.follows([case_statuses, case_descriptions]),
            case_descriptions])
        person_descriptions = search_regex('(adult|senior|patient|life)s?') +\
            search_regex('child(ren)?|person|people')
        person_counts = ra.follows([
            count_descriptions,
            ra.label('case', person_descriptions)
        ], max_dist=50)
        case_descriptions_with_counts = ra.near([
            case_descriptions,
            ra.combine([
                ra.near([counts, count_modifiers, count_modifiers]),
                count_descriptions
            ], prefer='num_spans')
        ], max_dist=50)

        singular_case_spans = []
        for t_span in spacy_tokens.spans:
            token = t_span.token
            if token.lemma_ not in ['case', 'fatality', 'death', 'hospitalization']:
                continue
            if token.tag_ != 'NN':
                continue
            if not set(['a', 'an', 'the']).intersection([
                    c.lower_ for c in token.children]):
                continue
            singular_case_spans.append(t_span)

        # Use word sense disabiguation to omit phrases like "In the case of"
        # The sentence vectors from setences using the word "case" with
        # different meanings are compared to the sentence from the document.
        # The word sense from the most similar sentence is used.
        filtered_singular_case_spans = []
        for sentence, group in spacy_sentences.group_spans_by_containing_span(singular_case_spans):
            if len(group) == 0:
                continue
            case_count_sence_similary = max(sentence.span.similarity(x)
                                            for x in case_count_senses)
            non_case_count_sence_similary = max(sentence.span.similarity(x)
                                                for x in non_case_count_senses)
            if case_count_sence_similary > non_case_count_sence_similary:
                filtered_singular_case_spans.extend(group)
        singular_case_spans = filtered_singular_case_spans

        singular_case_descriptions = []
        for count_description, group in AnnoTier(case_descriptions).group_spans_by_containing_span(
                singular_case_spans, allow_partial_containment=True):
            if len(group) > 0:
                singular_case_descriptions.append(count_description)

        # remove counts that span multiple sentences
        all_potential_counts = reduce(lambda a, b: a + b, [
            case_descriptions_with_counts,
            # Ex: Deaths: 13
            ra.follows([
                search_regex('deaths(\s?:)?', 'death'),
                counts]),
            person_counts,
            count_descriptions,
            singular_case_descriptions])

        single_sentence_counts = []
        for sentence, group in spacy_sentences.group_spans_by_containing_span(all_potential_counts):
            single_sentence_counts += group

        annotated_counts = ra.combine(
            [single_sentence_counts], prefer='num_spans')

        attributes = [
            'annual',
            'approximate',
            'average',
            'case',
            'confirmed',
            'cumulative',
            'death',
            'hospitalization',
            'incremental',
            'max',
            'min',
            'monthly',
            'suspected',
            'weekly',
        ]
        count_spans = []
        for match in annotated_counts:
            match_dict = match.groupdict()
            matching_attributes = set([
                attr for attr in attributes
                if attr in match_dict
            ])
            if 'death' in matching_attributes or 'hospitalization' in matching_attributes:
                matching_attributes.add('case')
            if 'count' in match_dict:
                count = utils.parse_spelled_number(match_dict['count'][0].text)
            else:
                # For single case reports a count number might not be used.
                # Ex. A new case, the index case
                count = 1
            if 'range' in match_dict:
                range_match = match_dict['range'][0]
                upper_count_text = range_match.groupdict()['count'][0].text
                upper_count = utils.parse_spelled_number(upper_count_text)
                count_spans.append(CountSpan(match, {
                    'text': match.text,
                    'attributes': sorted(list(matching_attributes) + ['min']),
                    'count': count
                }))
                count_spans.append(CountSpan(range_match, {
                    'text': upper_count_text,
                    'attributes': sorted(list(matching_attributes) + ['max']),
                    'count': upper_count
                }))
            else:
                count_spans.append(CountSpan(match, {
                    'text': match.text,
                    'attributes': sorted(list(matching_attributes)),
                    'count': count
                }))
        return {'counts': AnnoTier(count_spans)}
