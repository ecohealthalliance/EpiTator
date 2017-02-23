#!/usr/bin/env python
import re
import pattern

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

def dehyphenate_numbers_and_ages(text):
    dehyphenateable_string_set = set(numbers.keys()) | set([
        "year",
        "old"
    ])
    outtext = ""
    last = 0
    for match in re.finditer("\S+", text):
        outtext += text[last:match.start()]
        if(
            '-' in match.string and len(match.string) > 1 and
            len(set(match.string.split('-')) & dehyphenateable_string_set) > 0
        ):
            outtext += re.sub("-", " ", text[match.start():match.end()])
        else:
            outtext += text[match.start():match.end()]
        last = match.end()
    outtext += text[last:]
    return outtext

def collapse_linebreaks(text):
    """
    Turn a series of 3 or more linebreaks into a series of just 3 linebreaks.
    """
    return re.sub(r"_{3,}", "___", text)

def parse_number(num):
    try:
        return int(num)
    except ValueError:
        try:
            return float(num)
        except ValueError:
            return None

def parse_spelled_number(tokens_or_str):
    """
    This uses the number() function in pattern.en to do most of the parsing.
    Instead of returning zero when the number can't be parsed it returns None
    and it can handle numbers delimited with spaces.
    """
    if isinstance(tokens_or_str, basestring):
        tokens = []
        for word in tokens_or_str.split(' '):
            if len(word) > 0:
                tokens.extend(word.split('-'))
    else:
        tokens = tokens_or_str
    if re.match('^\d+$', ''.join(tokens)):
        value = pattern.en.number(''.join(tokens))
    else:
        value = pattern.en.number(' '.join(tokens))
    if value == 0 and tokens[0] not in ['0', 'zero']:
        return None
    else:
        return value
    
def find_nearby_matches(text, start_offset, stop_offset, pattern):
    region_start = text[:start_offset].rfind(".")
    region_start = 0 if region_start < 0 else region_start
    region_end = text[stop_offset:].find(".")
    region_end = len(text) if region_end < 0 else stop_offset + region_end
    region = text[region_start:region_end]
    match_list = [region[m.start():m.end()].lower() for m in pattern.finditer(region)]
    return list(set(match_list))
    
def find_all_match_offsets(text, match):
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
        elif (
            len(text) > start_at + 1 and
            # Hyphens may be removed from the pattern text
            # so they are treated as spaces and can be skipped when aligning
            # the text.
            re.match(r"\s|-$", text[start_at])
        ):
            return match_constituents(
                text,
                constituents,
                start_at + 1)
        else:
            return None


    start_offset = 0
    offsets = []

    start_at = 0
    while start_offset > -1:

        first_constituent = match.constituents()[0].string
        start_offset = text.find(first_constituent, start_at)

        if start_offset > -1:
            stop_offset = match_constituents(
                text, match.constituents()[1:],
                start_offset + len(first_constituent)
            )
            if stop_offset is not None:
                start_at = stop_offset
                offsets.append({
                    'fullMatch': (start_offset, stop_offset)
                })
            else:
                # If we didn't find a stop offset, start looking again after
                # this match.
                start_at = start_offset + 1

    return offsets
import result_aggregators as ra
def restrict_match(match):
    """
    Return a restricted version of a pattern Match object that only includes
    the words in a chunk that don't violate their own constraint.
    """
    if isinstance(match, ra.MetaMatch):
        return ra.MetaMatch(map(restrict_match, match.matches), match.labels)
    return pattern.search.Match(
        match.pattern,
        words=filter(
            lambda x : match.constraint(x).match(x),
            match.words
        ),
        map=match._map1
    )
