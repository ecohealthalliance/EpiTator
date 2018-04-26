#!/usr/bin/env python
"""Create annotation tiers using spacy"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
import re
from .spacy_nlp import spacy_nlp


class TokenSpan(AnnoSpan):
    def __init__(self, token, doc):
        super(TokenSpan, self).__init__(
            token.idx,
            token.idx + len(token),
            doc)
        self.token = token

class SentSpan(AnnoSpan):
    def __init__(self, span, doc):
        super(SentSpan, self).__init__(
            span.start_char,
            span.end_char,
            doc)
        self.span = span

class SpacyAnnotator(Annotator):
    def annotate(self, doc):
        tiers = {}
        ne_spans = []
        token_spans = []
        ne_chunk_start = None
        ne_chunk_end = None
        ne_chunk_type = None
        spacy_doc = spacy_nlp(doc.text)
        tiers['spacy.sentences'] = AnnoTier([
            SentSpan(sent, doc) for sent in spacy_doc.sents])
        for token in spacy_doc:
            start = token.idx
            end = token.idx + len(token)
            # White-space tokens are skipped.
            if not re.match(r"^\s", token.text):
                token_spans.append(TokenSpan(token, doc))
            if ne_chunk_start is not None and token.ent_iob_ != "I":
                ne_spans.append(AnnoSpan(ne_chunk_start, ne_chunk_end,
                                         doc, label=ne_chunk_type))
                ne_chunk_start = None
                ne_chunk_end = None
                ne_chunk_type = None
            if token.ent_type_:
                if token.ent_iob_ == "B":
                    ne_chunk_start = start
                    ne_chunk_end = end
                    ne_chunk_type = token.ent_type_
                elif token.ent_iob_ == "I":
                    ne_chunk_end = end
                elif token.ent_iob_ == "O":
                    ne_spans.append(AnnoSpan(start, end,
                                             doc, label=token.ent_type_))
                else:
                    raise Exception("Unexpected IOB tag: " + str(token.ent_iob_))
        if ne_chunk_start is not None:
            ne_spans.append(AnnoSpan(ne_chunk_start, ne_chunk_end,
                                     doc, label=ne_chunk_type))

        ambiguous_year_pattern = re.compile(r'\d{1,4}$', re.I)
        for ne_span in ne_spans:
            if ne_span.label == 'DATE' and ambiguous_year_pattern.match(ne_span.text):
                # Sometimes counts like 1500 are parsed as as the year component
                # of dates. This tries to catch that mistake when the year
                # is long enough ago that it is unlikely to be a date.
                date_as_number = int(ne_span.text)
                if date_as_number < 1900:
                    ne_span.label = 'QUANTITY'

        tiers['spacy.tokens'] = AnnoTier(token_spans)
        tiers['spacy.nes'] = AnnoTier(ne_spans)
        return tiers
