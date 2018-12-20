#!/usr/bin/env python
# coding=utf8
from __future__ import absolute_import
from __future__ import print_function
from . import maximum_weight_interval_set as mwis
import six
import re
from .annospan import AnnoSpan, SpanGroup
from .annotier import AnnoTier


class AnnoDoc(object):
    """
    A document to be annotated.
    The tiers property links to the annotations applied to it.
    """
    def __init__(self, text=None, date=None):
        if type(text) is six.text_type:
            self.text = text
        elif type(text) is str:
            self.text = six.text_type(text, 'utf8')
        else:
            raise TypeError("text must be string or unicode")
        self.tiers = {}
        self.date = date

    def __len__(self):
        return len(self.text)

    def add_tier(self, annotator, **kwargs):
        return self.add_tiers(annotator, **kwargs)

    def add_tiers(self, annotator, **kwargs):
        result = annotator.annotate(self, **kwargs)
        if isinstance(result, dict):
            self.tiers.update(result)
        return self

    def require_tiers(self, *tier_names, **kwargs):
        """
        Return the specified tiers or add them using the via annotator.
        """
        assert len(set(kwargs.keys()) | set(['via'])) == 1
        assert len(tier_names) > 0
        via_annotator = kwargs.get('via')
        tiers = [self.tiers.get(tier_name) for tier_name in tier_names]
        if all(t is not None for t in tiers):
            if len(tiers) == 1:
                return tiers[0]
            return tiers
        else:
            if via_annotator:
                self.add_tiers(via_annotator())
                return self.require_tiers(*tier_names)
            else:
                raise Exception("Tier could not be found. Available tiers: " + str(self.tiers.keys()))

    def create_regex_tier(self, regex, label=None):
        """
        Create an AnnoTier from all the spans of text that match the regex.
        """
        spans = []
        for match in re.finditer(regex, self.text):
            spans.append(
                SpanGroup([AnnoSpan(
                    match.start(),
                    match.end(),
                    self,
                    match.group(0))], label))
        return AnnoTier(spans, presorted=True)

    def to_dict(self):
        """
        Convert the document into a json serializable dictionary.
        This does not store all the document's data. For a complete
        serialization use pickle.

        >>> from .annospan import AnnoSpan
        >>> from .annotier import AnnoTier
        >>> import datetime
        >>> doc = AnnoDoc('one two three', date=datetime.datetime(2011, 11, 11))
        >>> doc.tiers = {
        ...     'test': AnnoTier([AnnoSpan(0, 3, doc), AnnoSpan(4, 7, doc)])}
        >>> d = doc.to_dict()
        >>> str(d['text'])
        'one two three'
        >>> str(d['date'])
        '2011-11-11T00:00:00Z'
        >>> sorted(d['tiers']['test'][0].items())
        [('label', None), ('textOffsets', [[0, 3]])]
        >>> sorted(d['tiers']['test'][1].items())
        [('label', None), ('textOffsets', [[4, 7]])]
        """
        json_obj = {
            'text': self.text
        }
        if self.date:
            json_obj['date'] = self.date.strftime("%Y-%m-%dT%H:%M:%S") + 'Z'
        json_obj['tiers'] = {}
        for name, tier in self.tiers.items():
            json_obj['tiers'][name] = [
                span.to_dict() for span in tier]
        return json_obj

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
