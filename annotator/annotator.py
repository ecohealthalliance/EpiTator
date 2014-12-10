#!/usr/bin/env python
"""Annotator"""
import json
import re
from lazy import lazy
from collections import defaultdict

from nltk import sent_tokenize

import pattern
import utils

import maximum_weight_interval_set as mwis

def tokenize(text):
    return sent_tokenize(text)

class Annotator(object):

    def annotate():
        """Take an AnnoDoc and produce a new annotation tier"""
        raise NotImplementedError("annotate method must be implemented in child")

class AnnoDoc(object):

    # TODO what if the original text needs to be later transformed, e.g.
    # stripped of tags? This will ruin offsets.

    def __init__(self, text=None, date=None):
        if type(text) is unicode or text:
            self.text = text
        elif type(text) is str:
            self.text = unicode(text, 'utf8')
        else:
            raise TypeError("text must be string or unicode")
        self.tiers = {}
        self.properties = {}
        self.pattern_tree = None
        self.date = date

    def find_match_offsets(self, match):
        """
        Returns the byte offsets of a pattern lib match object.
        """
        return (
            match.words[0].byte_offsets[0],
            match.words[-1].byte_offsets[-1]
        )

    def byte_offsets_to_pattern_match(self, offsets):
        """
        Create a pattern lib match object from the given byte offsets.
        """
        class ExternalMatch(pattern.search.Match):
            """
            A sequence of words that implements the pattern match interface.
            """
            def __init__(self, words):
                self.words = words
        start_word = self.__offset_to_word[offsets[0]]
        end_word = self.__offset_to_word[offsets[-1] - 1]
        return ExternalMatch(
            self.pattern_tree.all_words[
                start_word.abs_index:end_word.abs_index + 1
            ]
        )

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
            utils.dehyphenate_numbers_and_ages(self.text),
            lemmata=True,
            relations=True
        )
        # The pattern tree parser doesn't tag some numbers, such as 2, as CD (Cardinal number).
        # see: https://github.com/clips/pattern/issues/84
        # This code tags all the arabic numerals as CDs. It is a temporairy fix
        # that should be discarded when issue is resolved in the pattern lib.
        for sent in self.pattern_tree:
            for word in sent.words:
                if utils.parse_number(word.string) is not None:
                    word.tag = 'CD'
        # Annotate the words in the parse tree with their absolute index and
        # and create an array with all the words.
        abs_index = 0
        self.pattern_tree.all_words = []
        for sent in self.pattern_tree:
            for word in sent.words:
                # Pattern probably shouldn't be creating zero length words.
                # I've only encountered it happing with usual unicode chars
                # like \u2028
                # There might be other consequences when this happens.
                if len(word.string) > 0:
                    self.pattern_tree.all_words.append(word)
                    word.abs_index = abs_index
                    word.doc_word_array = self.pattern_tree.all_words
                    abs_index += 1
        # Create __offset_to_word array and add byte offsets to all the
        # words in the parse tree.
        text_offset = 0
        word_offset = 0
        self.__offset_to_word = [None] * len(self.text)
        while(
            text_offset < len(self.text) and
            word_offset < len(self.pattern_tree.all_words)
        ):
            word = self.pattern_tree.all_words[word_offset]
            # The match_len is the number of chars after the text_offset
            # that the match ends.
            # It needs to be computed because sometimes pattern lib
            # Words remove spaces that were present in the original text
            # e.g. :3 so we need to ignore spaces inside the original
            match_len = 0
            char_idx = 0
            while char_idx < len(word.string):
                word_char = word.string[char_idx]
                if text_offset + match_len >= len(self.text):
                    match_len = -1
                    break
                if self.text[text_offset + match_len] == word_char:
                    match_len += 1
                    char_idx += 1
                else:
                    whitespace = re.search(r"^\s*",
                        self.text[text_offset + match_len:],
                        re.UNICODE
                    ).end()
                    if whitespace == 0:
                        match_len = -1
                        break
                    else:
                        match_len += whitespace
            # Any number of periods is turned into a 3 period ellipsis,
            # so we need to include the extras in the match.
            if word.string == '...':
                match_len = re.match(r"^\.*", self.text[text_offset:]).end()
            
            if (
                word.string[0] == self.text[text_offset] and
                match_len > 0 and
                word.string[-1] == self.text[text_offset + match_len - 1]
            ):
                word.byte_offsets = (text_offset, text_offset + match_len)
                self.__offset_to_word[text_offset] = word
                text_offset += match_len
                word_offset += 1
            elif (
                # Hyphens may be removed from the pattern text
                # so they are treated as spaces and can be skipped when aligning
                # the text.
                re.match(r"^\s|-", self.text[text_offset], re.UNICODE)
            ):
                text_offset += 1
            else:
                raise Exception(
                    u"Cannot match word [" + word.string +
                    u"] with text [" + self.text[text_offset:text_offset + 10] +
                    u"]" +
                    u" match_len=" + unicode(match_len)
                )
        # Fill the empty offsets with their previous value
        prev_val = None
        for idx, value in enumerate(self.__offset_to_word):
            if value is not None:
                prev_val = value
            else:
                self.__offset_to_word[idx] = prev_val

        def p_search(query):
            # Add offsets:
            results = pattern.search.search(
                query,
                self.pattern_tree,
                taxonomy=self.taxonomy
            )
            # for r in results:
            #     r.sentence_idx = self.pattern_tree.sentences.index(r.words[0].sentence)
            return results


        self.p_search = p_search

    def add_tier(self, annotator, **kwargs):
        annotator.annotate(self, **kwargs)

    def to_json(self):
        json_obj = {'text': self.text,
                    'properties': self.properties}

        if self.date:
            json_obj['date'] = self.date.strftime("%Y-%m-%dT%H:%M:%S") + 'Z'

        if self.properties:
            json_obj['properties'] = self.properties

        json_obj['tiers'] = {}
        for name, tier in self.tiers.iteritems():
            json_obj['tiers'][name] = tier.to_json()

        return json.dumps(json_obj)

    def filter_overlapping_spans(self, tier_names=None):
        """Remove the smaller of any overlapping spans."""
        if not tier_names:
            tiers = self.tiers.keys()
        for tier_name in tier_names:
            if tier_name not in self.tiers: continue
            tier = self.tiers[tier_name]
            my_mwis = mwis.find_maximum_weight_interval_set([
                mwis.Interval(
                    start=span.start,
                    end=span.end,
                    weight=(span.end - span.start),
                    corresponding_object=span
                )
                for span in tier.spans
            ])
            tier.spans =  [
                interval.corresponding_object
                for interval in my_mwis
            ]

class AnnoTier(object):

    def __init__(self, spans=None):
        if spans is None:
            self.spans = []
        else:
            self.spans = spans

    def __repr__(self):
        return unicode([unicode(span) for span in self.spans])

    def __len__(self):
        return len(self.spans)

    def to_json(self):

        docless_spans = []
        for span in self.spans:
            span_dict = span.__dict__.copy()
            del span_dict['doc']
            docless_spans.append(span_dict)

        return json.dumps(docless_spans)

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

    def filter_overlapping_spans(self, score_func=None):
        """Remove the smaller of any overlapping spans."""
        my_mwis = mwis.find_maximum_weight_interval_set([
            mwis.Interval(
                start=span.start,
                end=span.end,
                weight=score_func(span) if score_func else (span.end - span.start),
                corresponding_object=span
            )
            for span in self.spans
        ])
        self.spans =  [
            interval.corresponding_object
            for interval in my_mwis
        ]

class AnnoSpan(object):

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

    def overlaps(self, other_span):
        return (
            (self.start >= other_span.start and self.start <= other_span.end) or
            (other_span.start >= self.start and other_span.start <= self.end)
        )

    def adjacent_to(self, other_span, max_dist=0):
        return (
            self.comes_before(other_span, max_dist) or
            other_span.comes_before(self, max_dist)
        )

    def comes_before(self, other_span, max_dist=0):
        # Note that this is a strict version of comes before where the
        # span must end before the other one starts.
        return (
            self.end >= other_span.start - max_dist - 1 and
            self.end < other_span.start
        )

    def extended_through(self, other_span):
        """
        Create a new span like this one but with it's range extended through
        the range of the other span.
        """
        return AnnoSpan(
            min(self.start, other_span.start),
            max(self.end, other_span.end),
            self.doc,
            self.label
        )

    def size(self): return self.end - self.start

    @lazy
    def text(self):
        return self.doc.text[self.start:self.end]

    def to_dict(self):
        """
        Return a json serializable dictionary.
        """
        return dict(
            label=self.label,
            textOffsets=[[self.start, self.end]]
        )
