#!/usr/bin/env python
"""Token Annotator"""

import nltk

from annotator import *

class TokenAnnotator:

    def __init__(self, tokenizer=None):
        """"""
        if tokenizer:
            self.tokenizer = tokenizer
        else:
            self.tokenizer = nltk.tokenize.WordPunctTokenizer()

    def annotate_doc(self, doc):
        for sentence in doc.sentences:
            self.annotate_sentence(sentence)

    def annotate_sentence(self, sentence):

        tokens = self.tokenizer.tokenize(sentence.text)

        # Walk through the tokens and consume the string with them in
        # order to figure out the byte offests occupied by each token.
        # Optionally account for a space between each token.
        # NB -- this space-accounting may not be appropriate for every kind
        # of tokenizer.

        spans = []
        index = 0
        tail = sentence.text

        for token in tokens:

            while not tail.startswith(token):
                # TODO make this safer. There are certain characters
                # that we should be willing to consume, but not all. There should
                # be an error raised if we find non-word-breaking characters
                # where we expected the next token.                
                index += 1
                tail = tail[1:]

            spans.append(AnnoSpan(index, index + len(token), sentence, label=token))
            index += len(token)
            tail = tail.replace(token, '', True)                

        sentence.tiers['tokens'] = AnnoTier(spans)
        # for span in sentence.tiers['tokens'].spans:
        #     print span.start, span.end, span.label
        # print "sentence.tiers['tokens'].spans[1].start", sentence.tiers['tokens'].spans[1].start
        return sentence



