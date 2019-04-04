#!/usr/bin/env python
"""Load a shared spacy model"""
import spacy
import os
import re
if os.environ.get('SPACY_MODEL_SHORTCUT_LINK'):
    spacy_nlp = spacy.load(os.environ.get('SPACY_MODEL_SHORTCUT_LINK'))
else:
    import en_core_web_md as spacy_model
    spacy_nlp = spacy_model.load()
sent_nlp = spacy.blank('en')

line_break_re = re.compile(r"\n{4,}")


def custom_sentencizer(doc_text):
    """
    A modified version of the default sentencizer_strategy that also breaks
    on sequences of more than 4 spaces.
    """
    doc = sent_nlp(doc_text)
    start = 0
    seen_sent_end = False
    for i, word in enumerate(doc):
        word.is_sent_start = i == 0
        if seen_sent_end and not word.is_punct:
            yield doc[start:word.i]
            start = word.i
            word.is_sent_start = True
            seen_sent_end = False
        elif word.text in ['.', '!', '?'] or line_break_re.match(word.text):
            seen_sent_end = True
    if start < len(doc):
        doc[start].is_sent_start = True
        yield doc[start:len(doc)]
