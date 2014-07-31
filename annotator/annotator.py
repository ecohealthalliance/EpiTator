#!/usr/bin/env python
"""Annotator"""
from lazy import lazy

from nltk import sent_tokenize

import pattern
import utils

def tokenize(text):
    return sent_tokenize(text)

class Annotator:

    def annotate():
        """Take an AnnoDoc and produce a new annotation tier"""
        raise NotImplementedError("annotate method must be implemented in child")

class AnnoDoc:

    # TODO what if the original text needs to be later transformed, e.g.
    # stripped of tags? This will ruin offsets.

    def __init__(self, text=None):
        if type(text) is unicode:
            self.text = text
        elif type(text) is str:
            self.text = unicode(text, 'utf8')
        else:
            raise TypeError("text must be string or unicode")
        self.tiers = {}
        self.properties = {}
        self.pattern_tree = None
        
    def setup_pattern(self):
        """
        Parse the doc with pattern so we can use the pattern.search module on it
        """
        if self.pattern_tree:
            # Document is already parsed.
            return
        self.taxonomy = pattern.search.Taxonomy()
        self.taxonomy.append(pattern.search.WordNetClassifier())
        self.pattern_tree = pattern.en.parsetree(
            self.text,
            lemmata=True,
            relations=True
        )
        # The pattern tree parser doesn't tag some numbers, such as 2, as CD (Cardinal number).
        # see: https://github.com/clips/pattern/issues/84
        # This monkey patch tags all the arabic numerals as CDs.
        for sent in self.pattern_tree:
            for word in sent.words:
                if utils.parse_number(word.string) is not None:
                    word.tag = 'CD'
        def p_search(query):
            return pattern.search.search(
                query,
                self.pattern_tree,
                taxonomy=self.taxonomy
            )
            
        self.p_search = p_search
        
    def add_tier(self, annotator):
        annotator.annotate(self)

class AnnoTier:

    def __init__(self, spans=None):
        if spans is None:
            self.spans = []
        else:
            self.spans = spans

    def __repr__(self):
        return unicode([unicode(span) for span in self.spans])

    def __len__(self):
        return len(self.spans)

    def next_span(self, span):
        """Get the next span after this one"""
        index = self.spans.index(span)
        if index == len(self.spans) - 1:
            return None
        else:
            return self.spans[index + 1]

    def spans_over(self, start, end=None):
        """Get all spans which overlap a position or range"""
        if not end: end = start + 1
        return filter(lambda span: len(set(range(span.start, span.end)).
                                       intersection(range(start, end))) > 0,
                      self.spans)

    def spans_in(self, start, end):
        """Get all spans which are contained in a range"""
        return filter(lambda span: span.start >= start and span.end <= end,
                      self.spans)

    def spans_at(self, start, end):
        """Get all spans with certain start and end positions"""
        return filter(lambda span: start == span.start and end == span.end,
                      self.spans)

    def spans_over_span(self, span):
        """Get all spans which overlap another span"""
        return self.spans_over(span.start, span.end)

    def spans_in_span(self, span):
        """Get all spans which lie within a span"""
        return self.spans_in(span.start, span.end)

    def spans_at_span(self, span):
        """Get all spans which have the same start and end as another span"""
        return self.spans_at(span.start, span.end)

    def spans_with_label(self, label):
        """Get all spans which have a given label"""
        return filter(lambda span: span.label == label, self.spans)

    def labels(self):
        """Get a list of all labels in this tier"""
        return [span.label for span in self.spans]

    def sort_spans(self):
        """Sort spans by order of start"""

        self.spans.sort(key=lambda span: span.start)

    # TODO needs testing
    def filter_overlapping_spans(self, decider=None):
        """Remove the smaller of any overlapping spans. Takes an optional
           decider function which takes two spans and returns False if span_a
           should not be retained, True if span_a should be retained."""

        retained_spans = []
        removed_spans_indexes = []

        a_index = -1
        for span_a in self.spans:
            a_index += 1
            retain_a = True
            b_index = -1
            for span_b in self.spans:
                b_index += 1
                if (not b_index in removed_spans_indexes and
                    a_index != b_index and
                    ((span_b.start in range(span_a.start, span_a.end)) or
                     (span_a.start in range(span_b.start, span_b.end))) and
                     span_b.size() >= span_a.size()):

                    if not decider or decider(span_a, span_b) is False:
                        retain_a = False
                        removed_spans_indexes.append(a_index)

            if retain_a:
                retained_spans.append(span_a)

        self.spans = retained_spans

class AnnoSpan:

    def __repr__(self):
        return u'{0}-{1}:{2}'.format(self.start, self.end, self.label)

    def __init__(self, start, end, doc, label=None):
        self.start = start
        self.end = end
        self.doc = doc

        if label == None:
            self.label = self.text
        else:
            self.label = label

    def size(self): return self.end - self.start

    @lazy
    def text(self):
        return self.doc.text[self.start:self.end]


