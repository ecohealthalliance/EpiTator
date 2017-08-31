#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import
from lazy import lazy


class AnnoSpan(object):
    """
    A span of text with an annotation applied to it.
    """
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
        Create a new span that includes this one and the other span.
        """
        return SpanGroup([self, other_span], self.label)

    def size(self):
        return self.end - self.start

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


class SpanGroup(AnnoSpan):
    """
    A AnnoSpan that extends through a group of AnnoSpans.
    """
    def __init__(self, base_spans, label=None):
        assert isinstance(base_spans, list)
        assert len(base_spans) > 0
        self.base_spans = base_spans
        self.start = min([s.start for s in base_spans])
        self.end = max([s.end for s in base_spans])
        self.doc = base_spans[0].doc
        self.label = label

    def __repr__(self):
        return ("SpanGroup("
                "text=" + self.text + ", "
                "label=" + str(self.label) + ", " +
                ", ".join(map(str, self.base_spans)) + ")")

    def groupdict(self):
        """
        Return a dict with all the labeled matches.
        """
        out = {}
        for base_span in self.base_spans:
            if isinstance(base_span, SpanGroup):
                for key, values in base_span.groupdict().items():
                    out[key] = out.get(key, []) + values
        if self.label:
            out[self.label] = [self]
        return out

    def iterate_base_spans(self):
        """
        Recursively iterate over all base_spans including base_spans of child MatchSpans.
        """
        for span in self.base_spans:
            yield span
            if isinstance(span, SpanGroup):
                for span2 in span.iterate_base_spans():
                    yield span2

    def iterate_leaf_base_spans(self):
        """
        Return the leaf base spans in a SpanGroup tree.
        """
        for span in self.iterate_base_spans():
            if not isinstance(span, SpanGroup):
                yield span
