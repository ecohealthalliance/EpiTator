#!/usr/bin/env python
"""Create annotation tiers using spacy"""
from annotator import Annotator, AnnoSpan, AnnoTier
import re
import en_depent_web_md
spacy_nlp = en_depent_web_md.load()

class SpacyAnnotator(Annotator):
    def annotate(self, doc):
        ne_spans = []
        token_spans = []
        ne_chunk_start = None
        ne_chunk_end = None
        ne_chunk_type = None
        for token in spacy_nlp(doc.text):
            # White-space tokens are skipped.
            if not re.match(r"^\s", token.text):
                token_spans.append(
                    AnnoSpan(token.idx, token.idx + len(token),
                        doc, label=token.text))
            if ne_chunk_start != None and token.ent_iob_ != "I":
                ne_spans.append(AnnoSpan(ne_chunk_start, ne_chunk_end,
                    doc, label=ne_chunk_type))
                ne_chunk_start = None
                ne_chunk_end = None
                ne_chunk_type = None
            if token.ent_type_:
                if token.ent_iob_ == "B":
                    ne_chunk_start = token.idx
                    ne_chunk_end = token.idx + len(token)
                    ne_chunk_type = token.ent_type_
                elif token.ent_iob_ == "I":
                    ne_chunk_end = token.idx + len(token)
                elif token.ent_iob_ == "O":
                    ne_spans.append(AnnoSpan(token.idx, token.idx + len(token),
                        doc, label=token.ent_type_))
        if ne_chunk_start != None:
            ne_spans.append(AnnoSpan(ne_chunk_start, ne_chunk_end,
                doc, label=ne_chunk_type))
        doc.tiers['spacy.tokens'] = AnnoTier(token_spans)
        doc.tiers['spacy.nes'] = AnnoTier(ne_spans)
        return doc
