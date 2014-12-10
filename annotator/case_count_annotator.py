#!/usr/bin/env python
"""
Annotate case/death/hospitalization counts
"""
import re
from collections import defaultdict

import pattern.search, pattern.en

from annotator import *

import utils

cumulative_pattern = re.compile('|'.join(["total", "sum", "brings to", "in all", "already"]), re.I)
def find_cumulative_keywords(text, start_offset, stop_offset):
    return utils.find_nearby_matches(text, start_offset, stop_offset, cumulative_pattern)

modifier_pattern = re.compile('|'.join(["average", "mean", "median", "annual"]), re.I)
def find_modifier_keywords(text, start_offset, stop_offset):
    return utils.find_nearby_matches(text, start_offset, stop_offset, modifier_pattern)

class CaseCountAnnotator(Annotator):
    """Extract the case/death/hospitalization counts from some text.
    TODO: This should be use the output of the location and time extraction
    so to return more detailed count information. E.g. We could infer that
    a count only applies to a specific location/time.
    """
    def get_matches(self, count_pattern, text, search_fun):

        matches = search_fun(count_pattern)
        retained_matches = []

        for match in matches:
            number = utils.parse_spelled_number([s.string for s in match.group(1)])
            if number is not None:
                offsets_tuples = utils.find_all_match_offsets(text, match)
                for offsets_tuple in offsets_tuples:
                    # We now know the offsets of the full match, and need to
                    # find the offsets of the numeric match.
                    # TODO this is not safe, looking for the string that way.
                    # Hopefully the tokenization in the numeric group has not
                    # altered the actual string.
                    start_offset = offsets_tuple['fullMatch'][0]
                    stop_offset = offsets_tuple['fullMatch'][1]
                    num_start_offset = text[start_offset:stop_offset].find(
                        match.group(1).string
                    )
                    offsets_tuple['numericMatch'] = (
                        num_start_offset + start_offset,
                        num_start_offset + start_offset + len(match.group(1).string)
                    )
                    cumulative_keywords = find_cumulative_keywords(
                        text,
                        offsets_tuple['numericMatch'][0],
                        offsets_tuple['numericMatch'][1])
                    is_cumulative = len(cumulative_keywords) > 0

                    modifier_keywords = find_modifier_keywords(
                        text,
                        offsets_tuple['numericMatch'][0],
                        offsets_tuple['numericMatch'][1])

                    retained_matches.append(dict({
                        'value' : number,
                        'numericMatch' : match.group(1).string,
                        'fullMatch' : match.string,
                        'fullMatchOffsets' : [offsets_tuple['fullMatch'][0],
                                              offsets_tuple['fullMatch'][1]],
                        'textOffsets' : [offsets_tuple['numericMatch'][0],
                                         offsets_tuple['numericMatch'][1]],
                        'cumulative': is_cumulative,
                        'modifiers': modifier_keywords
                    }))
        return retained_matches

    def annotate(self, doc):
        doc.setup_pattern()
        number_pattern = '{CD+ and? CD? CD?}'

        count_patterns_and_types = [
            #VB* is used because some times the parse tree is wrong.
            #Ex: There have been 12 reported cases in Colorado.
            #Ex: There was one suspected case of bird flu in the country
            (number_pattern + ' JJ*? JJ*|VB*? PATIENT|CASE|INFECTION', 'caseCount'),
            (number_pattern + ' *? *? INFECT|AFFLICT', 'caseCount'),

            #Ex: it brings the number of cases reported in Jeddah since 27 Mar 2014 to 28
            #Ex: The number of cases has exceeded 30
            ('NUMBER OF PATIENT|CASE|INFECTION *? *? TO ' + number_pattern, 'caseCount'),
            ('NUMBER OF PATIENT|CASE|INFECTION VP ' + number_pattern, 'caseCount'),
            (number_pattern + ' NP? PATIENT|CASE? DIED|DEATHS|FATALITIES|KILLED', 'deathCount'),

            #Ex: it has already claimed about 455 lives in Guinea
            ('CLAIM *? ' + number_pattern + ' LIVES', 'deathCount'),
            ('DEATHS :? {CD+}', 'deathCount'),
            (number_pattern + ' NP? HOSPITALIZED', 'hospitalizationCount'),

            #Ex: 222 were admitted to hospitals with symptoms of diarrhea
            (number_pattern + ' NP? VP TO? HOSPITAL', 'hospitalizationCount')
        ]

        spans = []

        for count_pattern, count_type in count_patterns_and_types:
            pattern_matches = self.get_matches(
                count_pattern, doc.text, doc.p_search)

            for pattern_match in pattern_matches:
                offsets = pattern_match.get("textOffsets")
                span = AnnoSpan(offsets[0], offsets[1],
                                doc,
                                label=pattern_match.get("value"))
                span.type = count_type
                span.cumulative = pattern_match['cumulative']
                span.modifiers = pattern_match['modifiers']
                spans.append(span)

        doc.tiers['caseCounts'] = AnnoTier(spans)
        def span_score(span):
            """
            When spans overlap hospitalization counts and death counts
            are retained over case counts becaues they are more specific.
            """
            if span.type in ['hospitalizationCount', 'deathCount']:
                return 100 + span.end - span.start
            else:
                return span.end - span.start
        doc.tiers['caseCounts'].filter_overlapping_spans(score_func=span_score)
        doc.tiers['caseCounts'].sort_spans()

        return doc

if __name__ == '__main__':
    run_case_count_patterns()
