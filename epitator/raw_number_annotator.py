#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier
from .annospan import AnnoSpan, SpanGroup
from .spacy_annotator import SpacyAnnotator
from .date_annotator import DateAnnotator
from . import utils
import re


def is_valid_number(num_string):
    """
    Check that number can be parsed and does not begin with 0.
    """
    if num_string[0] == '0' and len(num_string) > 1:
        return False
    value = utils.parse_spelled_number(num_string)
    return value is not None


class RawNumberAnnotator(Annotator):

    def annotate(self, doc):
        if 'dates' not in doc.tiers:
            doc.add_tiers(DateAnnotator())
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        dates = doc.tiers['dates']
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_nes = doc.tiers['spacy.nes']
        numbers = []
        for ne_span in spacy_nes:
            if ne_span.label in ['QUANTITY', 'CARDINAL']:
                if is_valid_number(ne_span.text):
                    numbers.append(SpanGroup([ne_span], 'count'))
                else:
                    joiner_offsets = [m.span()
                                      for m in re.finditer(r'\s(?:to|and|or)\s',
                                                           ne_span.text)]
                    if len(joiner_offsets) == 1:
                        range_start = AnnoSpan(ne_span.start, ne_span.start + joiner_offsets[0][0], doc)
                        range_end = AnnoSpan(ne_span.start + joiner_offsets[0][1], ne_span.end, doc)
                        if is_valid_number(range_start.text):
                            numbers.append(SpanGroup([range_start], 'count'))
                        if is_valid_number(range_end.text):
                            numbers.append(SpanGroup([range_end], 'count'))

        # Add purely numeric numbers that were not picked up by the NER.
        numbers += spacy_tokens.search_spans(r'[1-9]\d{0,6}', 'count').without_overlaps(spacy_nes).spans
        # Add delimited numbers
        numbers += doc.create_regex_tier(r'[1-9]\d{1,3}((\s\d{3})+|(,\d{3})+)', 'count').spans
        # Remove counts that overlap a date
        numbers = AnnoTier(numbers).without_overlaps(dates)
        return {'raw_numbers': numbers}
