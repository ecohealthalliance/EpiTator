#!/usr/bin/env python
# coding=utf8
"""Annotator"""
from __future__ import absolute_import
from __future__ import print_function
import json
from lazy import lazy
from . import maximum_weight_interval_set as mwis
import six
from six.moves import range


class Annotator(object):

    def annotate():
        """Take an AnnoDoc and produce a new annotation tier"""
        raise NotImplementedError(
            "annotate method must be implemented in child")


class AnnoDoc(object):

    def __init__(self, text=None, date=None):
        if type(text) is six.text_type:
            self.text = text
        elif type(text) is str:
            self.text = six.text_type(text, 'utf8')
        else:
            raise TypeError("text must be string or unicode")
        self.tiers = {}
        self.properties = {}
        self.date = date

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
        for name, tier in self.tiers.items():
            json_obj['tiers'][name] = tier.to_json()

        return json.dumps(json_obj)

    def filter_overlapping_spans(self, tiers=None, tier_names=None, score_func=None):
        """Remove the smaller of any overlapping spans."""
        if not tiers:
            tiers = tier_names
        if not tiers:
            tiers = list(self.tiers.keys())
        intervals = []
        for tier in tiers:
            if isinstance(tier, six.string_types):
                tier_name = tier
                if tier_name not in self.tiers:
                    print("Warning! Tier does not exist:", tier_name)
                    continue
                tier = self.tiers[tier_name]
            intervals.extend([
                mwis.Interval(
                    start=span.start,
                    end=span.end,
                    weight=score_func(span) if score_func else (
                        span.end - span.start),
                    corresponding_object=(tier, span)
                )
                for span in tier.spans
            ])
            tier.spans = []
        my_mwis = mwis.find_maximum_weight_interval_set(intervals)
        for interval in my_mwis:
            tier, span = interval.corresponding_object
            tier.spans.append(span)


class AnnoTier(object):

    def __init__(self, spans=None):
        if spans is None:
            self.spans = []
        else:
            self.spans = sorted(spans)

    def __repr__(self):
        return six.text_type([six.text_type(span) for span in self.spans])

    def __len__(self):
        return len(self.spans)

    def to_json(self):
        docless_spans = []
        for span in self.spans:
            span_dict = span.__dict__.copy()
            del span_dict['doc']
            docless_spans.append(span_dict)
        return json.dumps(docless_spans)

    def group_spans_by_containing_span(self, other_tier, allow_partial_containment=False):
        """
        Group spans in the other tier by the spans that contain them.
        """
        if isinstance(other_tier, AnnoTier):
            other_spans = other_tier.spans
        else:
            other_spans = sorted(other_tier)
        other_spans_idx = 0
        for span in self.spans:
            span_group = []
            # iterate over the other spans that come before this span.
            while other_spans_idx < len(other_spans):
                if allow_partial_containment:
                    if other_spans[other_spans_idx].end > span.start:
                        break
                else:
                    if other_spans[other_spans_idx].start >= span.start:
                        break
                other_spans_idx += 1
            other_span_idx_2 = other_spans_idx
            while other_span_idx_2 < len(other_spans):
                if other_spans[other_span_idx_2].start >= span.end:
                    break
                if not allow_partial_containment:
                    # Skip the other span if it is not contained by this span.
                    # It is possible there is another shorter span that starts
                    # after it and is fully contained by this span.
                    if other_spans[other_span_idx_2].end > span.end:
                        other_span_idx_2 += 1
                        continue
                span_group.append(other_spans[other_span_idx_2])
                other_span_idx_2 += 1
            yield span, span_group

    def next_span(self, span):
        """Get the next span after this one"""
        index = self.spans.index(span)
        if index == len(self.spans) - 1:
            return None
        else:
            return self.spans[index + 1]

    def spans_over(self, start, end=None):
        """Get all spans which overlap a position or range"""
        if not end:
            end = start + 1
        return [span for span in self.spans if len(set(range(span.start, span.end)).
                                       intersection(list(range(start, end)))) > 0]

    def spans_in(self, start, end):
        """Get all spans which are contained in a range"""
        return [span for span in self.spans if span.start >= start and span.end <= end]

    def spans_at(self, start, end):
        """Get all spans with certain start and end positions"""
        return [span for span in self.spans if start == span.start and end == span.end]

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
        return [span for span in self.spans if span.label == label]

    def labels(self):
        """Get a list of all labels in this tier"""
        return [span.label for span in self.spans]

    def sort_spans(self):
        """Sort spans by order of start"""
        print("sort_spans is deprecated. AnnoTier spans are now always sorted.")

    def filter_overlapping_spans(self, score_func=None):
        """Remove the smaller of any overlapping spans."""
        my_mwis = mwis.find_maximum_weight_interval_set([
            mwis.Interval(
                start=span.start,
                end=span.end,
                weight=score_func(span) if score_func else (
                    span.end - span.start),
                corresponding_object=span
            )
            for span in self.spans
        ])
        self.spans = [
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

        if label is None:
            self.label = self.text
        else:
            self.label = label

    def __lt__(self, other):
        return self.start < other.start

    def __len__(self):
        return len(self.text)

    def overlaps(self, other_span):
        return (
            (self.start >= other_span.start and self.start < other_span.end) or
            (other_span.start >= self.start and other_span.start < self.end)
        )

    def contains(self, other_span):
        return self.start <= other_span.start and self.end >= other_span.end

    def adjacent_to(self, other_span, max_dist=0):
        return (
            self.comes_before(other_span, max_dist) or
            other_span.comes_before(self, max_dist)
        )

    def comes_before(self, other_span, max_dist=0, allow_overlap=False):
        if allow_overlap:
            ok_start = self.start <= other_span.start
        else:
            ok_start = self.end <= other_span.start
        return self.end >= other_span.start - max_dist - 1 and ok_start

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
