#!/usr/bin/env python
"""
Annotates counts with the following attributes:
cumulative, case, death, age, hospitalization, approximate, min, max
"""
from __future__ import absolute_import
import re
from .annotator import Annotator, AnnoTier, AnnoSpan
from .spacy_annotator import SpacyAnnotator
from . import result_aggregators as ra
from .result_aggregators import MatchSpan
from . import utils
import logging
from functools import reduce
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class CountSpan(AnnoSpan):
    attributes = [
        "annual",
        "approximate",
        "average",
        "case",
        "confirmed",
        "cumulative",
        "death",
        "hospitalization",
        "incremental",
        "max",
        "min",
        "monthly",
        "suspected",
        "weekly",
    ]

    def __init__(self, match_span):
        self.start = match_span.start
        self.end = match_span.end
        self.doc = match_span.doc
        self.label = match_span.text
        self.match = match_span
        match_dict = match_span.groupdict()
        attributes = set([
            attr for attr in self.attributes
            if attr in match_dict
        ])
        if 'death' in attributes:
            attributes.add('case')
        if 'count' in match_dict:
            count = utils.parse_spelled_number(match_dict['count'].text)
        else:
            # For single case reports a count number might not be used.
            # Ex. A new case, the index case
            count = 1
        self.metadata = {
            'text': match_span.text,
            'count': count,
            'attributes': sorted(list(attributes))
        }

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
        logger.info("Cannot parse count string: " + count_string)
        return False
    if value > 1000000000:
        return False
    return True


def search_spans_for_regex(regex_term, spans, match_name=None):
    regex = re.compile(r"^" + regex_term + r"$", re.I)
    match_spans = []
    for span in spans:
        if regex.match(span.text):
            match_spans.append(MatchSpan(span, match_name))
    return match_spans


class CountAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tier(SpacyAnnotator())
        counts = []
        for ne_span in doc.tiers['spacy.nes'].spans:
            if ne_span.label in ['QUANTITY', 'CARDINAL'] and is_valid_count(ne_span.text):
                counts.append(MatchSpan(ne_span, 'count'))
            elif ne_span.label == 'DATE' and is_valid_count(ne_span.text):
                # Sometimes counts like 1500 are parsed as as the year component
                # of dates. This tries to catched that mistake when the year
                # is long enough ago that it is unlikely to be a date.
                date_as_number = utils.parse_spelled_number(ne_span.text)
                if date_as_number and date_as_number < 1900:
                    counts.append(MatchSpan(ne_span, 'count'))

        def search_regex(regex_term, match_name=None):
            return search_spans_for_regex(
                regex_term, doc.tiers['spacy.tokens'].spans, match_name)
        # Remove counts that overlap an age
        counts = ra.remove_overlaps(counts,
                                    ra.follows([search_regex('age'),
                                                search_regex('of'), counts]))
        # Remove distances
        counts = ra.remove_overlaps(counts,
                                    ra.follows([counts,
                                                search_regex('kilometers|km|miles|mi')]))
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
                     search_regex(r'died|killed|claimed|fatalities|fatality') +
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
        for t_span in doc.tiers['spacy.tokens'].spans:
            token = t_span.token
            if token.lemma_ not in ['case', 'death', 'hospitalization']:
                continue
            if token.tag_ != 'NN':
                continue
            if not set(['a', 'an', 'the']).intersection([
                    c.lower_ for c in token.children]):
                continue
            singular_case_spans.append(t_span)

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
        for sentence, group in doc.tiers['spacy.sentences'].group_spans_by_containing_span(all_potential_counts):
            single_sentence_counts += group

        annotated_counts = ra.combine(
            [single_sentence_counts], prefer='num_spans')

        return {
            'counts': AnnoTier([
                CountSpan(count)
                for count in annotated_counts
            ])}
