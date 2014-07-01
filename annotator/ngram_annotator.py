#!/usr/bin/env python
"""Token Annotator"""

import nltk

from annotator import *
from token_annotator import TokenAnnotator

class NgramAnnotator:

    def __init__(self, tokenizer=None):
        pass

    def annotate_doc(self, doc):
        for sentence in doc.sentences:
            self.annotate_sentence(sentence)

    def annotate_sentence(self, sentence, n_min=1, n_max=7):

        if not 'tokens' in sentence.tiers:
            token_annotator = TokenAnnotator()
            token_annotator.annotate_sentence(sentence)

        sentence.tiers['ngrams'] = AnnoTier()
        for n in range(n_min, n_max + 1):
            sentence.tiers[str(n) + 'grams'] = AnnoTier()

        token_spans = sentence.tiers['tokens'].spans

        for n in range(n_min, n_max + 1):
            for i in range(len(token_spans)):
                if i + n > len(token_spans):
                    break
                span = AnnoSpan(token_spans[i].start,
                                token_spans[i + n - 1].end,
                                sentence)
                sentence.tiers['ngrams'].spans.append(span)
                sentence.tiers[str(n) + 'grams'].spans.append(span)

        # Remove any ngram tiers for which there are no ngrams
        for n in range(n_min, n_max + 1):
            if len(sentence.tiers[str(n) + 'grams'].spans) == 0:
                del(sentence.tiers[str(n) + 'grams'])

        return sentence

        