#!/usr/bin/env python
"""Token Annotator"""

import nltk

from annotator import *

class TokenAnnotator:

    def __init__(self, tokenizer=nltk.tokenize.WordPunctTokenizer()):
        """tokenizer should be a function that takes a string and returns a
           list of token strings"""
        self.tokenizer = tokenizer

    def annotate(self, doc):

        tokens = self.tokenizer.tokenize(doc.text)

        # Walk through the tokens and consume the string with them in
        # order to figure out the byte offests occupied by each token.
        # Optionally account for a space between each token.
        # NB -- this space-accounting may not be appropriate for every kind
        # of tokenizer.

        spans = []
        index = 0
        tail = doc.text

        for token in tokens:

            while not tail.startswith(token):
                # TODO make this safer. There are certain characters
                # that we should be willing to consume, but not all. There should
                # be an error raised if we find non-word-breaking characters
                # where we expected the next token.                
                index += 1
                tail = tail[1:]

            spans.append(AnnoSpan(index, index + len(token), doc, label=token))
            index += len(token)
            tail = tail.replace(token, '', True)                

        doc.tiers['tokens'] = AnnoTier(spans)

        return doc



