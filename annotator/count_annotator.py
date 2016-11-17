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

class MatchSpan(AnnoSpan):
    """
    Class is used internally for creating temporary annotiers from match objects.
    """
    def __init__(self, match, doc):
        self.start, self.end = doc.find_match_offsets(match)
        self.doc = doc
        self.label = match.string
        self.match = match

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

class CountAnnotator(Annotator):
    def annotate(self, doc):
        if 'times' not in doc.tiers:
            jvm_nlp_annotator = JVMNLPAnnotator(['times'])
            doc.add_tier(jvm_nlp_annotator)
        doc.setup_pattern()
        my_search = doc.p_search
        counts = ra.label('count', my_search('{CD+ and? CD? CD?}'))
        # Cull the false-positive counts
        # Remove counts that have fractional values, begin with 0
        # or are extremely large
        def is_valid(count_string):
            value = utils.parse_spelled_number(count_string)
            if count.string[0] == '0': return False
            if int(value) != value: return False
            if value > 1000000000: return False
            return True
        match_tier = AnnoTier([
            MatchSpan(count, doc)
            for count in counts if is_valid(count.string)
        ])
        # Remove counts that overlap a time span.
        doc.filter_overlapping_spans(
            ['times', match_tier],
            score_func=lambda x: 0 if isinstance(x, MatchSpan) else 1)
        counts = [span.match for span in match_tier.spans]
        # Remove counts that overlap an age
        counts = ra.combine([
            counts,
            ra.follows([my_search('AGE OF'), counts])
        ], remove_conflicts=True)
        count_modifiers = ra.combine([
            ra.label('average', my_search('AVERAGE|MEAN')) +
            ra.label('annual', my_search('ANNUAL|ANNUALLY')) +
            ra.label('monthly', my_search('MONTHLY')) +
            ra.label('weekly', my_search('WEEKLY')) +
            ra.label('cumulative', my_search('TOTAL|CUMULATIVE|ALREADY')) +
            ra.label('incremental', my_search('NEW|ADDITIONAL|RECENT')) +
            ra.label('max', my_search('LESS|BELOW|UNDER|MOST|MAXIMUM|UP')) +
            ra.label('min', my_search('GREATER|ABOVE|OVER|LEAST|MINIMUM|DOWN|EXCEED')) +
            ra.label('approximate', my_search('APPROXIMATELY|ABOUT|NEAR|AROUND')),
        ])
        count_descriptions = ra.near([count_modifiers, counts]) + counts
        case_descriptions = map(utils.restrict_match, (
            ra.label('death',
                my_search('DIED|DEATH|FATALITIES|KILLED|CLAIMED')
            ) +
            ra.label('hospitalization',
                my_search('HOSPITAL|HOSPITALIZED')
            ) +
            ra.label('case',
                my_search(
                    'CASE|INFECTION|INFECT|STRICKEN'
                )
            )
        ))
        case_statuses = map(utils.restrict_match, (
            ra.label('suspected',
                my_search('SUSPECTED')
            ) +
            ra.label('confirmed',
                my_search('CONFIRMED')
            )
        ))
        case_descriptions = ra.combine([
            ra.follows([case_statuses, case_descriptions]),
            case_descriptions
        ])
        person_descriptions = map(utils.restrict_match, my_search('PERSON|CHILD|ADULT|ELDER|PATIENT|LIFE'))
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
                ra.label('death', my_search('DEATHS :?')),
                counts
            ]),
            person_counts,
            count_descriptions
        ], prefer='match_length')
        doc.tiers['counts'] = AnnoTier([
            CountSpan(count, doc)
            for count in annotated_counts
        ])
        doc.tiers['counts'].sort_spans()
        return doc
