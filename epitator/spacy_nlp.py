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


def sentencizer_strategy(doc):
    """
    A modified version of the default sentencizer_strategy that also breaks
    on sequences of more than 4 spaces.
    """
    start = 0
    seen_sent_end = False
    for i, word in enumerate(doc):
        if seen_sent_end and not word.is_punct:
            yield doc[start:word.i]
            start = word.i
            seen_sent_end = False
        elif word.text in ['.', '!', '?'] or line_break_re.match(word.text):
            seen_sent_end = True
    if start < len(doc):
        yield doc[start:len(doc)]


sent_nlp.add_pipe(sent_nlp.create_pipe('sentencizer', config={
    'strategy': sentencizer_strategy}))
