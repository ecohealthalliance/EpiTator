#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import
import json
import six
import re
from . import result_aggregators as ra
from .annospan import SpanGroup, AnnoSpan


class AnnoTier(object):
    """
    A group of AnnoSpans stored sorted by start offset.
    """
    def __init__(self, spans=None, presorted=False):
        if spans is None:
            self.spans = []
        elif isinstance(spans, AnnoTier):
            self.spans = list(spans.spans)
        else:
            if presorted:
                self.spans = spans
            else:
                self.spans = sorted(spans)

    def __repr__(self):
        return ('AnnoTier([' +
                ', '.join([six.text_type(span) for span in self.spans]) +
                '])')

    def __len__(self):
        return len(self.spans)

    def __add__(self, other_tier):
        return AnnoTier(self.spans + other_tier.spans)

    def __iter__(self):
        return iter(self.spans)

    def __getitem__(self, idx):
        return self.spans[idx]

    def to_json(self):
        docless_spans = []
        for span in self.spans:
            span_dict = span.__dict__.copy()
            del span_dict['doc']
            docless_spans.append(span_dict)
        return json.dumps(docless_spans)

    def group_spans_by_containing_span(self,
                                       other_tier,
                                       allow_partial_containment=False):
        """
        Group spans in the other tier by the spans that contain them.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three')
        >>> tier_a = AnnoTier([AnnoSpan(0, 3, doc), AnnoSpan(4, 7, doc)])
        >>> tier_b = AnnoTier([AnnoSpan(0, 1, doc)])
        >>> list(tier_a.group_spans_by_containing_span(tier_b))
        [(0-3:one, [0-1:o]), (4-7:two, [])]
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

    def spans_contained_by_span(self, selector_span):
        """
        Return a list of spans that are contained by a "selector span".

        >>> from epitator.annospan import AnnoSpan
        >>> from epitator.annodoc import AnnoDoc
        >>> from epitator.annotier import AnnoTier
        >>> doc = AnnoDoc('one two three')
        >>> tier1 = AnnoTier([AnnoSpan(0, 3, doc), AnnoSpan(4, 7, doc)])
        >>> span1 = AnnoSpan(3, 9, doc)
        >>> tier1.spans_contained_by_span(span1)
        AnnoTier([4-7:two])
        """
        return(
            AnnoTier([span for span in self if selector_span.contains(span)])
        )

    def spans_overlapped_by_span(self, selector_span):
        """
        Return a list of spans that overlap a "selector span".

        >>> from epitator.annospan import AnnoSpan
        >>> from epitator.annodoc import AnnoDoc
        >>> from epitator.annotier import AnnoTier
        >>> doc = AnnoDoc('one two three')
        >>> tier1 = AnnoTier([AnnoSpan(0, 3, doc), AnnoSpan(4, 7, doc)])
        >>> span1 = AnnoSpan(0, 1, doc)
        >>> tier1.spans_overlapped_by_span(span1)
        AnnoTier([0-3:one])
        """
        return(
            AnnoTier([span for span in self if selector_span.overlaps(span)])
        )

    def with_label(self, label):
        """
        Create a tier from the spans which have the given label

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc, 'odd'),
        ...                  AnnoSpan(4, 7, doc, 'even'),
        ...                  AnnoSpan(8, 13, doc, 'odd')])
        >>> tier.with_label("odd")
        AnnoTier([0-3:odd, 8-13:odd])
        """
        return AnnoTier([span for span in self if span.label == label])

    def optimal_span_set(self, prefer="text_length"):
        """
        Create a tier with the set of non-overlapping spans from this tier that
        maximizes the prefer function.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc, 'odd'),
        ...                  AnnoSpan(4, 7, doc, 'even'),
        ...                  AnnoSpan(3, 13, doc, 'long_span'),
        ...                  AnnoSpan(8, 13, doc, 'odd')])
        >>> tier.optimal_span_set()
        AnnoTier([0-3:odd, 3-13:long_span])
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

    def with_contained_spans_from(self, other_tier, allow_partial_containment=False):
        """
        Create a new tier from pairs spans in this tier and the other tier
        where the span in this tier contains one in the other tier.
        """
        span_groups = self.group_spans_by_containing_span(other_tier,
                                                          allow_partial_containment=allow_partial_containment)
        result = []
        for span, group in span_groups:
            for other_span in group:
                result.append(SpanGroup([span, other_span]))
        return AnnoTier(result)

    def with_nearby_spans_from(self, other_tier, max_dist=100):
        """
        Create a new tier from pairs spans in this tier and the other tier
        that are near eachother.
        """
        return AnnoTier(ra.near([self, other_tier], max_dist=max_dist))

    def with_following_spans_from(self, other_tier, max_dist=1, allow_overlap=False):
        """
        Create a new tier from pairs of spans where the one in the other tier follows a span from this tier.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three four')
        >>> tier1 = AnnoTier([AnnoSpan(0, 3, doc),
        ...                   AnnoSpan(8, 13, doc)])
        >>> tier2 = AnnoTier([AnnoSpan(14, 18, doc)])
        >>> tier1.with_following_spans_from(tier2)
        AnnoTier([SpanGroup(text=three four, label=None, 8-13:three, 14-18:four)])
        """
        extended_spans = []
        for span in self:
            extended_spans.append(
                AnnoSpan(span.start, span.end + max_dist + 1, span.doc, metadata=span))
        extended_spans = AnnoTier(extended_spans, presorted=True)
        span_groups = extended_spans.group_spans_by_containing_span(other_tier,
                                                                    allow_partial_containment=True)
        if allow_overlap:
            def starts_before_f(span_a, span_b):
                return span_a.start < span_b.start
        else:
            def starts_before_f(span_a, span_b):
                return span_a.end <= span_b.start
        result = []
        for extended_span, span_group in span_groups:
            idx = 0
            for span in span_group:
                if starts_before_f(extended_span.metadata, span):
                    break
                idx += 1
            for span in span_group[idx:]:
                result.append(SpanGroup([extended_span.metadata, span]))
        return AnnoTier(result)

    def combined_adjacent_spans(self, max_dist=1):
        """
        Create a new tier from groups of spans within max_dist of eachother.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three four')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc),
        ...                  AnnoSpan(8, 13, doc),
        ...                  AnnoSpan(14, 18, doc)])
        >>> tier.combined_adjacent_spans()
        AnnoTier([SpanGroup(text=one, label=None, 0-3:one), SpanGroup(text=three four, label=None, 8-13:three, 14-18:four)])
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

    def nearest_prior_span(self, target_span):
        """
        Find the nearest span that comes before the target span.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three four')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc),
        ...                  AnnoSpan(8, 13, doc),
        ...                  AnnoSpan(14, 18, doc)])
        >>> tier.nearest_prior_span(AnnoSpan(4, 7, doc))
        AnnoSpan(text=one)
        """
        closest_span = None
        for span in self:
            if span.start >= target_span.end:
                break
            closest_span = span
        return closest_span

    def label_spans(self, label):
        """
        Create a new tier based on this one 
        with labeled spans that can be looked up by groupdict.
        """
        return AnnoTier([SpanGroup([span], label) for span in self], presorted=True)

    def search_spans(self, regex, label=None):
        regex = re.compile(regex + r'$', re.I)
        match_spans = []
        for span in self:
            if regex.match(span.text):
                match_spans.append(SpanGroup([span], label))
        return AnnoTier(match_spans, presorted=True)
