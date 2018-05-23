#!/usr/bin/env python
"""Create annotation tiers using spacy"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
import re
from .spacy_nlp import spacy_nlp, sent_nlp


class TokenSpan(AnnoSpan):
    __slots__ = ['token']

    def __init__(self, token, doc, offset=0):
        super(TokenSpan, self).__init__(
            token.idx + offset,
            token.idx + len(token) + offset,
            doc)
        self.token = token


class SentSpan(AnnoSpan):
    __slots__ = ['span']

    def __init__(self, span, doc, offset=0):
        super(SentSpan, self).__init__(
            span.start_char + offset,
            span.end_char + offset,
            doc)
        self.span = span


class SpacyAnnotator(Annotator):
    def annotate(self, doc):
        tiers = {}
        ne_spans = []
        token_spans = []
        noun_chunks = []
        # SpaCy's neural nets currently use up too much memory on large docs,
        # so the document is divided into sections before recognizing named
        # entities. Each section is composed of N sentences. Sentence parsing
        # is not memory constrained.
        # https://github.com/explosion/spaCy/issues/1636
        sentences = AnnoTier([
            SentSpan(sent, doc) for sent in sent_nlp(doc.text).sents])
        tiers['spacy.sentences'] = sentences
        group_size = 10
        for sent_group_idx in range(0, len(sentences), group_size):
            doc_offset = sentences.spans[sent_group_idx].start
            sent_group_end = sentences.spans[min(sent_group_idx + group_size, len(sentences)) - 1].end
            ne_chunk_start = None
            ne_chunk_end = None
            ne_chunk_type = None
            spacy_doc = spacy_nlp(doc.text[doc_offset:sent_group_end])
            noun_chunks.extend(SentSpan(chunk, doc, offset=doc_offset) for chunk in spacy_doc.noun_chunks)
            for token in spacy_doc:
                start = token.idx + doc_offset
                end = start + len(token)
                # White-space tokens are skipped.
                if not re.match(r"^\s", token.text):
                    token_spans.append(TokenSpan(token, doc, offset=doc_offset))
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

        tiers['spacy.noun_chunks'] = AnnoTier(noun_chunks, presorted=True)
        tiers['spacy.tokens'] = AnnoTier(token_spans, presorted=True)
        tiers['spacy.nes'] = AnnoTier(ne_spans, presorted=True)
        return tiers
