#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import


EMPTY_LIST = []


class AnnoSpan(object):
    """
    A span of text with an annotation applied to it.
    """
    __slots__ = ["start", "end", "doc", "metadata", "label", "base_spans"]

    def __init__(self, start, end, doc, label=None, metadata=None):
        self.start = start
        self.end = end
        self.doc = doc
        self.metadata = metadata
        # Base spans is only non-empty on span groups.
        self.base_spans = EMPTY_LIST

        if label is None:
            self.label = self.text
        else:
            self.label = label

    def __repr__(self):
        return u'AnnoSpan({0}-{1}, {2})'.format(self.start, self.end, self.label)

    def __lt__(self, other):
        if self.start < other.start:
            return True
        elif self.start == other.start:
            return len(self) < len(other)
        else:
            return False

    def __len__(self):
        return len(self.text)

    def overlaps(self, other_span):
        return (
            (self.start >= other_span.start and self.start < other_span.end) or
            (other_span.start >= self.start and other_span.start < self.end)
        )

    def contains(self, other_span):
        return self.start <= other_span.start and self.end >= other_span.end

    def adjacent_to(self, other_span, max_dist=1):
        return (
            self.comes_before(other_span, max_dist) or
            other_span.comes_before(self, max_dist)
        )

    def comes_before(self, other_span, max_dist=1, allow_overlap=False):
        """
        Return True if the span comes before the other_span and there are
        max_dist or fewer charaters between them.

        >>> from .annotier import AnnoTier
        >>> from .annodoc import AnnoDoc
        >>> doc = AnnoDoc('one two three')
        >>> tier = AnnoTier([AnnoSpan(0, 3, doc), AnnoSpan(4, 7, doc)])
        >>> tier.spans[0].comes_before(tier.spans[1])
        True
        >>> tier.spans[1].comes_before(tier.spans[0])
        False
        """
        if allow_overlap:
            ok_start = self.start <= other_span.start
        else:
            ok_start = self.end <= other_span.start
        return ok_start and self.end >= other_span.start - max_dist

    def extended_through(self, other_span):
        """
        Create a new span that includes this one and the other span.
        """
        return SpanGroup([self, other_span], self.label)

    def trimmed(self):
        start = self.start
        end = self.end
        doc_text = self.doc.text
        while doc_text[start] == " " and start < end:
            start += 1
        while doc_text[end - 1] == " " and start < end:
            end -= 1
        return AnnoSpan(start, end, self.doc)

    def size(self):
        return self.end - self.start

    @property
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

    def groupdict(self):
        """
        Return a dict with all the labeled matches.
        """
        out = {}
        for base_span in self.base_spans:
            for key, values in base_span.groupdict().items():
                out[key] = out.get(key, []) + values
        if self.label:
            out[self.label] = [self]
        return out

    def iterate_base_spans(self):
        """
        Recursively iterate over all base_spans including base_spans of child SpanGroups.
        """
        for span in self.base_spans:
            yield span
            for span2 in span.iterate_base_spans():
                yield span2

    def iterate_leaf_base_spans(self):
        """
        Return the leaf base spans in a SpanGroup tree.
        """
        for span in self.iterate_base_spans():
            if not isinstance(span, SpanGroup):
                yield span

    def combined_metadata(self):
        """
        Return the merged metadata dictionaries from all descendant spans.
        Presedence of matching properties follows the order of a pre-order tree traversal.
        """
        leaf_spans = list(self.iterate_base_spans())
        leaf_spans.reverse()
        result = {}
        for leaf_span in leaf_spans + [self]:
            if leaf_span.metadata:
                result.update(leaf_span.metadata)
        return result


class SpanGroup(AnnoSpan):
    """
    A AnnoSpan that extends through a group of AnnoSpans.
    """
    def __init__(self, base_spans, label=None):
        assert isinstance(base_spans, list)
        assert len(base_spans) > 0
        super(SpanGroup, self).__init__(
            min(s.start for s in base_spans),
            max(s.end for s in base_spans),
            base_spans[0].doc)
        self.base_spans = base_spans
        self.label = label

    def __repr__(self):
        return ("SpanGroup("
                "text=" + self.text + ", "
                "label=" + str(self.label) + ", " +
                ", ".join(map(str, self.base_spans)) + ")")
