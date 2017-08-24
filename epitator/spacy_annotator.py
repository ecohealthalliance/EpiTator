#!/usr/bin/env python
"""Create annotation tiers using spacy"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
import re
from .spacy_nlp import spacy_nlp


class TokenSpan(AnnoSpan):
    def __init__(self, token, doc):
        self.doc = doc
        self.start = token.idx
        self.end = token.idx + len(token)
        self.label = token.text
        self.token = token


class SentSpan(AnnoSpan):
    def __init__(self, span, doc):
        self.doc = doc
        self.start = span.start_char
        self.end = span.end_char
        self.label = span.text
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
        if ne_chunk_start is not None:
            ne_spans.append(AnnoSpan(ne_chunk_start, ne_chunk_end,
                                     doc, label=ne_chunk_type))
        tiers['spacy.tokens'] = AnnoTier(token_spans)
        tiers['spacy.nes'] = AnnoTier(ne_spans)
        return tiers
