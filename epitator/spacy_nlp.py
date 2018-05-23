#!/usr/bin/env python
"""Load a shared spacy model"""
import spacy
import os
if os.environ.get('SPACY_MODEL_SHORTCUT_LINK'):
    spacy_nlp = spacy.load(os.environ.get('SPACY_MODEL_SHORTCUT_LINK'))
else:
    import en_core_web_md as spacy_model
    spacy_nlp = spacy_model.load()
sent_nlp = spacy.blank('en')
sent_nlp.add_pipe(sent_nlp.create_pipe('sentencizer'))