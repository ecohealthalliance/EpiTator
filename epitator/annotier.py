#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import
import json
import six
import re
from .annospan import SpanGroup, AnnoSpan
from . import maximum_weight_interval_set as mwis


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
        [(AnnoSpan(0-3, one), [AnnoSpan(0-1, o)]), (AnnoSpan(4-7, two), [])]
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
        AnnoTier([AnnoSpan(4-7, two)])
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
        AnnoTier([AnnoSpan(0-3, one)])
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
        AnnoTier([AnnoSpan(0-3, odd), AnnoSpan(8-13, odd)])
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
        AnnoTier([AnnoSpan(0-3, odd), AnnoSpan(3-13, long_span)])
        """
        all_spans = self.spans

        def first(x):
            """
            Perfers the matches that appear first in the first result list.
            """
            # Using an exponent makes it so that a first match will be prefered
            # over multiple non-overlapping later matches.
            return 2 ** (len(all_spans) - all_spans.index(x))

        def text_length(x):
            """
            Prefers the match with the longest span of text that contains all the
            matching content.
            """
            return len(x)

        def num_spans(x):
            """
            Prefers the match with the most distinct base spans.
            """
            if isinstance(x, SpanGroup):
                return len(set(x.iterate_leaf_base_spans()))
            else:
                return 1

        def num_spans_and_no_linebreaks(x):
            """
            Same as num_spans, but linebreaks are avoided as a secondary objective,
            and overall text length is minimized as a third objective.
            """
            return num_spans(x), int("\n" not in x.text), -len(x)

        if prefer == "first":
            prefunc = first
        elif prefer == "text_length":
            prefunc = text_length
        elif prefer == "num_spans":
            prefunc = num_spans
        elif prefer == "num_spans_and_no_linebreaks":
            prefunc = num_spans_and_no_linebreaks
        else:
            prefunc = prefer
        my_mwis = mwis.find_maximum_weight_interval_set([
            mwis.Interval(
                start=match.start,
                end=match.end,
                weight=prefunc(match),
                corresponding_object=match
            )
            for match in all_spans
        ])
        return AnnoTier([
            interval.corresponding_object
            for interval in my_mwis
        ])

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
        return AnnoTier(
            self.with_following_spans_from(other_tier, max_dist=max_dist, allow_overlap=True) +
            other_tier.with_following_spans_from(self, max_dist=max_dist, allow_overlap=True))

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
        AnnoTier([SpanGroup(text=three four, label=None, AnnoSpan(8-13, three), AnnoSpan(14-18, four))])
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
        AnnoTier([SpanGroup(text=one, label=None, AnnoSpan(0-3, one)), SpanGroup(text=three four, label=None, AnnoSpan(8-13, three), AnnoSpan(14-18, four))])
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

    def chains(self, at_least=1, at_most=None, max_dist=1):
        """
        Create a new tier from all chains of spans within max_dist of eachother.
        """
        combined_spans = AnnoTier()
        new_combined_spans = self
        chain_len = 1
        while True:
            if chain_len >= at_least:
                combined_spans += new_combined_spans
            if len(new_combined_spans) == 0:
                break
            chain_len += 1
            if at_most and chain_len > at_most:
                break
            new_combined_spans = new_combined_spans.with_following_spans_from(self, max_dist=max_dist)
        return combined_spans

    def span_before(self, target_span, allow_overlap=True):
        """
        Find the nearest span that comes before the target span.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three four')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc),
        ...                  AnnoSpan(8, 13, doc),
        ...                  AnnoSpan(14, 18, doc)])
        >>> tier.span_before(AnnoSpan(4, 7, doc))
        AnnoSpan(0-3, one)
        """
        closest_span = None
        for span in self:
            if span.start >= target_span.start:
                break
            if not allow_overlap and span.end > target_span.start:
                break
            closest_span = span
        return closest_span

    def span_after(self, target_span):
        """
        Find the nearest span that comes after the target span.
        """
        span = None
        for span in self:
            if span.start >= target_span.end:
                break
        return span

    def label_spans(self, label):
        """
        Create a new tier based on this one
        with labeled spans that can be looked up by groupdict.
        """
        return AnnoTier([SpanGroup([span], label) for span in self], presorted=True)

    def search_spans(self, regex, label=None):
        """
        Search spans for ones matching the given regular expression.
        """
        regex = re.compile(regex + r'$', re.I)
        match_spans = []
        for span in self:
            if regex.match(span.text):
                match_spans.append(SpanGroup([span], label))
        return AnnoTier(match_spans, presorted=True)

    def match_subspans(self, regex):
        """
        Create a new tier from the components of spans matching the given
        regular expression.

        >>> from .annospan import AnnoSpan
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three four')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc),
        ...                  AnnoSpan(4, 13, doc),
        ...                  AnnoSpan(14, 18, doc)])
        >>> tier.match_subspans(r"two")
        AnnoTier([AnnoSpan(4-7, two)])
        """
        regex = re.compile(regex)
        match_spans = []
        for span in self:
            for match in regex.finditer(span.text):
                match_spans.append(AnnoSpan(
                    match.start() + span.start,
                    match.end() + span.start,
                    span.doc
                ))
        return AnnoTier(match_spans, presorted=True)
