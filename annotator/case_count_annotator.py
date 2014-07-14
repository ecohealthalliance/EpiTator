#!/usr/bin/env python
"""Token Annotator"""

import re
from collections import defaultdict

import pymongo
import pattern.search, pattern.en

from annotator import *

class CaseCountAnnotator(Annotator):

    def __init__(self):
        pass

    def get_taxonomy(self):
        taxonomy = pattern.search.Taxonomy()
        taxonomy.append(pattern.search.WordNetClassifier())
        return taxonomy

    def get_matches(self, count_pattern, text, tree, taxonomy):
        matches = pattern.search.search(count_pattern, tree, taxonomy=taxonomy)
        retained_matches = []
        for m in matches:
            print "match", m.group(1)
            n = self.parse_spelled_number([s.string for s in m.group(1)])
            print 'parsed:', n
            if n is not None:
                print "m.string", m.string
                start_offsets = self.find_all(text, m.string)
                for start_offset in start_offsets:
                    retained_matches.append(dict({
                        'value' : n,
                        'fullMatch' : m.group(1).string,
                        'textOffsets' : [start_offset, start_offset + len(m.group(1).string)]
                    }))
        return retained_matches


    def find_all(self, string, substring):
        """Find all occurrences of a string in another string, returning the 
           start offsets"""
        i = 0
        while True:
            i = string.find(substring, i)
            if i == -1:
                return
            else:
                yield i
                i += len(substring)

    def annotate(self, doc):

        taxonomy = self.get_taxonomy()

        tree = pattern.en.parsetree(doc.text, lemmata=True)
        for sent in tree.sentences:
            for word in sent.words:
                if self.parse_number(word.string) is not None:
                    word.tag = 'CD'


        number_pattern = '{CD+ and? CD? CD?}'
    
        count_patterns_and_types = [
            (number_pattern + ' JJ*? JJ*|VB*? PATIENT|CASE|INFECTION', 'caseCount'),
            (number_pattern + ' *? *? INFECT|AFFLICT', 'caseCount'),
            ('NUMBER OF PATIENT|CASE|INFECTION *? *? TO ' + number_pattern, 'caseCount'),
            ('NUMBER OF PATIENT|CASE|INFECTION VP ' + number_pattern, 'caseCount'),
            (number_pattern + ' NP? PATIENT|CASE? DIED|DEATHS|FATALITIES|KILLED', 'deathCount'),
            ('CLAIM *? ' + number_pattern + ' LIVES', 'deathCount'),
            ('DEATHS :? {CD+}', 'deathCount'),
            (number_pattern + ' NP? HOSPITALIZED', 'hospitalizationCount'),
            (number_pattern + ' NP? VP TO? HOSPITAL', 'hospitalizationCount')
        ]

        spans = []

        for count_pattern, count_type in count_patterns_and_types:
            pattern_matches = self.get_matches(
                count_pattern, doc.text, tree, taxonomy)
            for pattern_match in pattern_matches:
                offsets = pattern_match.get("textOffsets")
                span = AnnoSpan(offsets[0], offsets[1], 
                                doc,
                                label=pattern_match.get("value"))
                span.type = count_type
                spans.append(span)

        doc.tiers['caseCounts'] = AnnoTier(spans)
        doc.tiers['caseCounts'].filter_overlapping_spans()

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
