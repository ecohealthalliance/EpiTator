#!/usr/bin/env python
"""
Annotates counts with the following attributes:
cumulative, case, death, age, hospitalization, approximate, min, max
"""
import re
from collections import defaultdict
from annotator import Annotator, AnnoTier, AnnoSpan
from jvm_nlp_annotator import JVMNLPAnnotator
import result_aggregators as ra
import utils
import logging
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
    def __init__(self, count_match, doc):
        offsets_tuple = doc.find_match_offsets(count_match)
        self.start = offsets_tuple[0]
        self.end = offsets_tuple[1]
        self.doc = doc
        self.label = count_match.string
        self.match = count_match
        match_dict = count_match.groupdict()
        attributes = set([
            attr for attr in self.attributes
            if attr in match_dict
        ])
        if 'death' in attributes:
            attributes.add('case')
        self.metadata = {
            'text': count_match.string,
            'count': utils.parse_spelled_number(match_dict['count'].string),
            'attributes': sorted(list(attributes))
        }
    def to_dict(self):
        result = super(CountSpan, self).to_dict()
        result.update(self.metadata)
        return result

class MatchSpan(AnnoSpan):
    """
    This class includes the words and string attributes from
    pattern match objects so it can be used by result aggregators.
    """
    def __init__(self, base_span, words):
        self.start = base_span.start
        self.end = base_span.end
        self.doc = base_span.doc
        self.label = self.text
        self.words = words
        self.string = self.text

class WordSpan(AnnoSpan):
    """
    This class includes the attributes from pattern word objects so it can be
    used by result aggregators.
    """
    def __init__(self, token_span, index):
        self.start = token_span.start
        self.end = token_span.end
        self.doc = token_span.doc
        self.label = token_span.label
        self.abs_index = index
        self.sentence = self.doc.tiers['stanford.sentences'].spans_over_span(token_span)[0]
        self.string = self.text
        self.byte_offsets = [token_span.start, token_span.end]
         # This is linked to the word tier span array after it is created.
        self.doc_word_array = None
    def groupdict(self):
        return {}

def is_valid_count(count_string):
    """
    Cull the false-positive counts
    Remove counts that have fractional values, begin with 0
    or are extremely large
    """
    value = utils.parse_spelled_number(count_string)
    if count_string[0] == '0': return False
    try:
        if int(value) != value: return False
    except (TypeError, ValueError) as e:
        logger.info("Cannot parse count string: " + count_string)
        return False
    if value > 1000000000: return False
    return True

class CountAnnotator(Annotator):
    def annotate(self, doc):
        doc.setup_pattern()
        if 'stanford.times' not in doc.tiers:
            jvm_nlp_annotator = JVMNLPAnnotator([
                'times', 'nes', 'sentences', 'tokens'])
            doc.add_tier(jvm_nlp_annotator)
        word_tier = AnnoTier([WordSpan(span, idx)
            for idx, span in enumerate(doc.tiers['stanford.tokens'].spans)])
        for span in word_tier.spans:
            span.doc_word_array = word_tier.spans
        count_matches = []
        ne_span_groups = doc.tiers['stanford.nes'].group_spans_by_containing_span(word_tier)
        for ne_span, word_spans in ne_span_groups:
            if ne_span.type == 'NUMBER' and is_valid_count(ne_span.text):
                count_matches.append(MatchSpan(ne_span, word_spans))
        counts = ra.label('count', count_matches)
        def search_regex(regex_term):
            regex = re.compile(r"^" + regex_term + r"$", re.I)
            match_spans = []
            for word_span in word_tier.spans:
                if regex.match(word_span.text):
                    match_spans.append(
                        MatchSpan(AnnoSpan(
                            word_span.start,
                            word_span.end,
                            doc,
                            regex), [word_span]))
            return match_spans
        # Remove counts that overlap an age
        counts = ra.combine([
            counts,
            ra.follows([search_regex('age'), search_regex('of'), counts])
        ], remove_conflicts=True)
        # Remove distances
        counts = ra.combine([
            counts,
            ra.follows([counts, search_regex('kilometers|km|miles|mi')])
        ], remove_conflicts=True)
        count_modifiers = ra.combine([
            ra.label('average', search_regex('average|mean')) +
            ra.label('annual', search_regex('annual(ly)?')) +
            ra.label('monthly', search_regex('monthly')) +
            ra.label('weekly', search_regex('weekly')) +
            ra.label('cumulative',
                search_regex('total|cumulative|already')) +
            ra.label('incremental',
                search_regex('(new|additional|recent)(ly)?')) +
            ra.label('max',
                search_regex('less|below|under|most|maximum|up')) +
            ra.label('min',
                search_regex('greater|above|over|least|minimum|down|exceeds?')) +
            ra.label('approximate',
            search_regex('approximate(ly)?|about|near(ly)?|around'))])
        count_descriptions = ra.near([count_modifiers, counts]) + counts
        case_descriptions = (
            ra.label('death',
                search_regex(r'died|killed|claimed|fatalities|fatality') +
                search_regex(r'deaths?')) +
            ra.label('hospitalization',
                #Ex: admitted to hospitals
                search_regex(r'hospitals?') +
                search_regex(r'hospitaliz(ations?|ed|es?|ing)')) +
            ra.label('case',
                search_regex(r'cases?') +
                search_regex(r'infections?|infect(ed|ing|s)?') +
                search_regex(r'stricken')))
        case_statuses = (
            ra.label('suspected',
                search_regex(r'suspect(ed|s|ing)?')) +
            ra.label('confirmed',
                search_regex(r'confirmed')))
        case_descriptions = ra.combine([
            ra.follows([case_statuses, case_descriptions]),
            case_descriptions])
        person_descriptions = search_regex('(adult|senior|patient|life)s?') +\
            search_regex('child(ren)?|person|people')
        person_counts = ra.follows([
            count_descriptions,
            ra.label('case', person_descriptions)
        ], 2)
        case_descriptions_with_counts = ra.near([
            case_descriptions,
            ra.combine([
                ra.near([counts, count_modifiers]) +
                ra.near([counts, count_modifiers, count_modifiers], outer=False),
                count_descriptions
            ], prefer='match_length')
        ], 3)
        annotated_counts = ra.combine([
            case_descriptions_with_counts,
            #Ex: Deaths: 13
            ra.follows([
                ra.label('death', search_regex('deaths( :)?')),
                counts]),
            person_counts,
            count_descriptions
        ], prefer='match_length')
        doc.tiers['counts'] = AnnoTier([
            CountSpan(count, doc)
            for count in annotated_counts
        ])
        doc.tiers['counts'].sort_spans()
        return doc
