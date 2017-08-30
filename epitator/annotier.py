#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import
from __future__ import print_function
import json
from . import maximum_weight_interval_set as mwis
import six
from . import result_aggregators as ra
from .annospan import SpanGroup

class AnnoTier(object):
    """
    A group of AnnoSpans stored sorted by start offset.
    """
    def __init__(self, spans=None):
        if spans is None:
            self.spans = []
        elif isinstance(spans, AnnoTier):
            self.spans = list(spans.spans)
        else:
            self.spans = sorted(spans)

    def __repr__(self):
        return six.text_type([six.text_type(span) for span in self.spans])

    def __len__(self):
        return len(self.spans)

    def __add__(self, other_tier):
        return AnnoTier(self.spans + other_tier.spans)

    def __iter__(self):
        return iter(self.spans)

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

    def spans_in(self, start, end):
        """Get all spans which are contained in a range"""
        return [span for span in self.spans
                if span.start >= start and span.end <= end]

    def spans_at(self, start, end):
        """Get all spans with certain start and end positions"""
        return [span for span in self.spans
                if start == span.start and end == span.end]

    def spans_in_span(self, span):
        """Get all spans which lie within a span"""
        return self.spans_in(span.start, span.end)

    def spans_at_span(self, span):
        """Get all spans which have the same start and end as another span"""
        return self.spans_at(span.start, span.end)

    def with_label(self, label):
        """Create a tier from the spans which have a given label"""
        return AnnoTier([span for span in self if span.label == label])

    def optimal_span_set(self, prefer="text_length"):
        """
        Return a tier with overlapping spans removed in such a way that the
        prefer function is maximized.
        """
        return AnnoTier(ra.combine([self.spans], prefer=prefer))

    def without_overlaps(self, other_tier):
        """
        Create a copy of this tier without spans that overlap a span in the
        other tier.
        """
        span_groups = self.group_spans_by_containing_span(other_tier,
                                                          allow_partial_containment=True)
        result = []
        for span, group in span_groups:
            if len(group) == 0:
                result.append(span)
        return AnnoTier(result)

    def with_nearby_spans_from(self, other_tier, max_dist=100):
        """
        Create a new tier from pairs spans in this tier and the other tier
        that are near eachother.
        """
        return AnnoTier(ra.near([self, other_tier], max_dist=max_dist))

    def combined_adjacent_spans(self, max_dist=1):
        """
        Create a new tier from groups of spans within max_dist of eachother.
        """
        prev_span = None
        span_groups = []
        span_group = None
        for span in self:
            if not prev_span:
                span_group = [span]
            elif prev_span.end + max_dist >= span.start:
                span_group.append(span)
            else:
                span_groups.append(SpanGroup(span_group))
                span_group = [span]
            prev_span = span
        if span_group:
            span_groups.append(SpanGroup(span_group))
        return AnnoTier(span_groups)
