#!/usr/bin/env python
"""Load a shared spacy model"""
import spacy
import os
if os.environ.get('SPACY_MODEL_SHORTCUT_LINK'):
    spacy_nlp = spacy.load(os.environ.get('SPACY_MODEL_SHORTCUT_LINK'))
else:
    import en_core_web_sm as spacy_model
    spacy_nlp = spacy_model.load()
