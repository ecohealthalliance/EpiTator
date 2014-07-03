#!/usr/bin/env python
"""Sentnece Annotator"""

from nltk import sent_tokenize

from annotator import *
from token_annotator import TokenAnnotator

class SentenceAnnotator(Annotator):

    def __init__(self, breaker=sent_tokenize):
        """Optional breaker should be a function that takes a string and returns
           a list of sentence strings"""

        self.breaker = breaker

    def annotate(self, doc):
        """Takes AnnoDoc string and returns an AnnoTier"""

        sentences = self.breaker(doc.text)

        spans = []
        index = 0
        tail = doc.text

        for sentence in sentences:

            while not tail.startswith(sentence):
                # TODO should we object if we have to consume a lot of characters
                # that don't look like they should have broken the sentence?
                index += 1
                tail = tail[1:]

            spans.append(AnnoSpan(index, index + len(sentence), doc))
            index += len(sentence)
            tail = tail.replace(sentence, '', True)                

        doc.tiers['sentences'] = AnnoTier(spans)

        return doc

        