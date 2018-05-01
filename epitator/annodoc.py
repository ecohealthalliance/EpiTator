#!/usr/bin/env python
# coding=utf8
"""Annotator"""
from __future__ import absolute_import
from __future__ import print_function
import json
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
        self.properties = {}
        self.date = date

    def add_tier(self, annotator, **kwargs):
        return self.add_tiers(annotator, **kwargs)

    def add_tiers(self, annotator, **kwargs):
        result = annotator.annotate(self, **kwargs)
        if isinstance(result, dict):
            self.tiers.update(result)
        return self

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
