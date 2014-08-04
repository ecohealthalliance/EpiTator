#!/usr/bin/env python
"""Token Annotator"""

import re
from collections import defaultdict

import pattern.search, pattern.en

from annotator import *


cumulative_pattern = re.compile('|'.join(["total", "sum", "brings to", "in all", "already"]), re.I)
def find_cumulative_keywords(text, start_offset, stop_offset):
    return find_nearby_matches(text, start_offset, stop_offset, cumulative_pattern)

modifier_pattern = re.compile('|'.join(["average", "mean", "median", "annual"]), re.I)
def find_modifier_keywords(text, start_offset, stop_offset):
    return find_nearby_matches(text, start_offset, stop_offset, modifier_pattern)

def find_nearby_matches(text, start_offset, stop_offset, pattern):
    region_start = text[:start_offset].rfind(".")
    region_start = 0 if region_start < 0 else region_start
    region_end = text[stop_offset:].find(".")
    region_end = len(text) if region_end < 0 else stop_offset + region_end
    region = text[region_start:region_end]
    match_list = [region[m.start():m.end()].lower() for m in pattern.finditer(region)]
    return list(set(match_list))

class CaseCountAnnotator(Annotator):
    """Extract the case/death/hospitalization counts from some text.
    TODO: This should be use the output of the location and time extraction
    so to return more detailed count information. E.g. We could infer that
    a count only applies to a specific location/time.
    """
    def __init__(self):
        self.taxonomy = pattern.search.Taxonomy()
        self.taxonomy.append(pattern.search.WordNetClassifier())

    def get_matches(self, count_pattern, text, tree):

        matches = pattern.search.search(count_pattern, tree, taxonomy=self.taxonomy)
        retained_matches = []

        for match in matches:
            number = self.parse_spelled_number([s.string for s in match.group(1)])
            if number is not None:
                offsets_tuples = self.find_all_match_offsets(text, match)
                for offsets_tuple in offsets_tuples:

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

    def find_all_match_offsets(self, text, match):
        """Find all occurrences of the match constituents in the target string,
           returning the offsets in the string for the full match as well as the
           numeric portion of the match.

           This is not straightforward because we don't know exactly how pattern
           has tokenized the input text, so a match on:
                Deaths: 900
           might have three tokens:
                'Deaths', ':', and '900',
           and when it's put back together as a string, it's:
                Deaths : 900
           Therefore we have to allow for spaces to exist or not exist separating
           match constituents that aren't strictly alphabetic."""

        def match_constituents(text, constituents, start_at=0):
            """Return None if all constituents cannot be found in sequence at the
               start of the string, otherwise, return the stop_offset of the
               last constituent."""

            if len(constituents) == 0:
                return start_at
            elif text[start_at:].startswith(constituents[0].string):
                return match_constituents(
                    text,
                    constituents[1:],
                    start_at + len(constituents[0].string))
            elif (len(text) > start_at + 1 and
                  text[start_at] == ' ' and
                  text[start_at + 1:].startswith(constituents[0].string)):
                return match_constituents(
                    text,
                    constituents[1:],
                    start_at + len(constituents[0].string) + 1)
            else:
                return None


        start_offset = 0
        offsets = []

        start_at = 0
        while start_offset > -1 :

            first_constituent = match.constituents()[0].string
            start_offset = text.find(first_constituent, start_at)

            if start_offset > -1:
                stop_offset = match_constituents(
                    text, match.constituents()[1:], start_offset + len(first_constituent))
                if stop_offset is not None:
                    start_at = stop_offset

                    # We now know the offsets of the full match, and need to
                    # find the offsets of the numeric match.
                    # TODO this is not safe, looking for the string that way.
                    # Hopefully the tokenization in the numeric group has not
                    # altered the actual string.
                    num_start_offset = text[start_offset:stop_offset].find(
                        match.group(1).string)

                    if num_start_offset > -1:
                        offsets.append(
                            {'fullMatch': (start_offset, stop_offset),
                             'numericMatch': (
                                num_start_offset + start_offset,
                                num_start_offset + start_offset + len(match.group(1).string))
                            }
                        )
                else:
                    # If we didn't find a stop offset, start looking again after
                    # this match.
                    start_at = start_offset + 1

        return offsets


    def annotate(self, doc):

        tree = pattern.en.parsetree(doc.text, lemmata=True)

        # The pattern tree parser doesn't tag some numbers, such as 2, as CD (Cardinal number).
        # see: https://github.com/clips/pattern/issues/84
        # This monkey patch tags all the arabic numerals as CDs.
        for sent in tree.sentences:
            for word in sent.words:
                if self.parse_number(word.string) is not None:
                    word.tag = 'CD'

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
                count_pattern, doc.text, tree)

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
        def decider(span_a, span_b):
            """Should span_a be retained if it overlaps with span_b? Yes, if it
                is a hospitalization count or death count and span_b is a case
                count, since the former are more specific than case counts."""
            if (span_a.type is 'caseCount' or
                span_b.type in ['hospitalizationCount', 'deathCount']):
                return False
            else:
                return True
        doc.tiers['caseCounts'].filter_overlapping_spans(decider=decider)
        doc.tiers['caseCounts'].sort_spans()

        return doc

    def parse_number(self, t):
        try:
            return int(t)
        except ValueError:
            try:
                return float(t)
            except ValueError:
                return None

    def parse_spelled_number(self, tokens):
        numbers = {
            'zero':0,
            'half': 1.0/2.0,
            'one':1,
            'two':2,
            'three':3,
            'four':4,
            'five':5,
            'six':6,
            'seven':7,
            'eight':8,
            'nine':9,
            'ten':10,
            'eleven':11,
            'twelve':12,
            'thirteen':13,
            'fourteen':14,
            'fifteen':15,
            'sixteen':16,
            'seventeen':17,
            'eighteen':18,
            'nineteen':19,
            'twenty':20,
            'thirty':30,
            'forty':40,
            'fifty':50,
            'sixty':60,
            'seventy':70,
            'eighty':80,
            'ninety':90,
            'hundred':100,
            'thousand':1000,
            'million': 1000000,
            'billion': 1000000000,
            'trillion':1000000000000,
            'gillion' :1000000000,
        }
        punctuation = re.compile(r'[\.\,\?\(\)\!]')
        affix = re.compile(r'(\d+)(st|nd|rd|th)')
        def parse_token(t):
            number = self.parse_number(t)
            if number is not None: return number
            if t in numbers:
                return numbers[t]
            else:
                return t
        cleaned_tokens = []
        for raw_token in tokens:
            for t in raw_token.split('-'):
                if t in ['and', 'or']: continue
                t = punctuation.sub('', t)
                t = affix.sub(r'\1', t)
                cleaned_tokens.append(t.lower())
        numeric_tokens = map(parse_token, cleaned_tokens)
        if any(filter(lambda t: isinstance(t, basestring), numeric_tokens)) or len(numeric_tokens) == 0:
            print 'Error: Could not parse number: ' + unicode(tokens)
            return
        number_out = 0
        idx = 0
        while idx < len(numeric_tokens):
            cur_t = numeric_tokens[idx]
            next_t = numeric_tokens[idx + 1] if idx + 1 < len(numeric_tokens) else None
            if next_t and cur_t < next_t:
                number_out += cur_t * next_t
                idx += 2
                continue
            number_out += cur_t
            idx += 1

        return number_out


if __name__ == '__main__':
    run_case_count_patterns()
