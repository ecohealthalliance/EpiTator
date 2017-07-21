#!/usr/bin/env python
"""
This annotates and parses dates and date ranges.
All dates are parsed as datetime ranges. For instance, a date like "11-6-87"
would be parsed as a range from the start of the day to the end of the day,
while a month like "December 2011" would be parsed as a range from the start
of December 1st to the end of December.
"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier, AnnoSpan
from .spacy_annotator import SpacyAnnotator
from . import result_aggregators as ra
from dateparser.date import DateDataParser
from dateutil.relativedelta import relativedelta
import re
import datetime

DATE_RANGE_JOINERS = r"to|through|until|untill|and"


class DateSpan(AnnoSpan):
    def __init__(self, base_span, datetime_range):
        self.start = base_span.start
        self.end = base_span.end
        self.doc = base_span.doc
        self.label = base_span.doc.text[base_span.start:base_span.end]
        self.datetime_range = datetime_range

    def to_dict(self):
        result = super(DateSpan, self).to_dict()
        result['datetime_range'] = self.datetime_range
        return result


class DateAnnotator(Annotator):
    def annotate(self, doc):
        strict_parser = DateDataParser(['en'], settings={
            'STRICT_PARSING': True})

        def date_to_datetime_range(text, relative_base=doc.date):
            # strip extra words from the date string
            text = re.sub(r"^(from\s)?(the\s)?"
                          r"((beginning|middle|start|end)\sof)?"
                          r"(between\s)?"
                          r"(late|mid|early)?\s?", "", text, re.I)
            # remove extra characters
            text = re.sub(r"\[|\]", "", text)
            # handle dates like "1950s" since dateparser doesn't
            decade_match = re.match(r"(\d{4})s", text)
            if decade_match:
                decade = int(decade_match.groups()[0])
                return [datetime.datetime(decade, 1, 1),
                        datetime.datetime(decade + 10, 1, 1)]
            parser = DateDataParser(['en'], settings={
                'RELATIVE_BASE': relative_base or datetime.datetime.now()})
            date_data = parser.get_date_data(text)
            if date_data['date_obj']:
                date = date_data['date_obj']
                if date_data['period'] == 'day':
                    return [date, date + relativedelta(days=1)]
                elif date_data['period'] == 'month':
                    date = datetime.datetime(date.year, date.month, 1)
                    return [date, date + relativedelta(months=1)]
                elif date_data['period'] == 'year':
                    date = datetime.datetime(date.year, 1, 1)
                    return [date, date + relativedelta(years=1)]
        if 'spacy.nes' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        # Create a combine tier of nes and regex dates
        date_spans = []
        for ne_span in doc.tiers['spacy.nes'].spans:
            if ne_span.label == 'DATE':
                date_spans.append(ne_span)
        # Regex for numerical dates
        regex = re.compile(
            r"\b(\d{1,4}\s?[\/\-]\s?\d{1,2}\s?[\/\-]\s?\d{1,4})\b", re.I)
        match_spans = []
        for match in re.finditer(regex, doc.text):
            match_spans.append(AnnoSpan(
                match.start(), match.end(), doc, match.group(0)))
        date_spans = sorted(date_spans + match_spans)
        # Group adjacent date info incase it is parsed as separate chunks.
        # ex: Friday, October 7th 2010.
        adjacent_date_spans = ra.follows([date_spans, date_spans], max_dist=9)
        adjacent_date_spans = ra.combine([
            ra.follows([adjacent_date_spans, date_spans], max_dist=9),
            adjacent_date_spans])
        adjacent_date_spans = ra.combine([
            ra.follows([adjacent_date_spans, date_spans], max_dist=9),
            adjacent_date_spans])
        grouped_date_spans = []
        for date_group in adjacent_date_spans:
            date_group_spans = list(date_group.iterate_leaf_base_spans())
            if any(strict_parser.get_date_data(span.text)['date_obj'] is None
                   for span in date_group_spans):
                extended_span = date_group_spans[0].extended_through(
                    date_group_spans[-1])
                if date_to_datetime_range(extended_span.text) is not None:
                    grouped_date_spans.append(extended_span)
        # Find date ranges by looking for joiner words between dates.
        date_range_spans = ra.follows([
            date_spans,
            [t_span for t_span in doc.tiers['spacy.tokens'].spans
             if re.match(r"("+DATE_RANGE_JOINERS+r"|\-)$", t_span.text, re.I)],
            date_spans], max_dist=1, label='date_range')

        tier_spans = []
        for date_span in ra.combine([date_range_spans,
                                     grouped_date_spans,
                                     date_spans], prefer='text_length'):
            # Parse the span text into one or two components depending on
            # whether it contains multiple dates for specifying a range.
            if isinstance(date_span, ra.MatchSpan) and\
               date_span.match_name == 'date_range':
                range_components = [span.text
                                    for span in date_span.base_spans[0::2]]
            else:
                range_components = re.split(
                    r"\b(?:"+DATE_RANGE_JOINERS+r")\b", date_span.text, re.I)
                if len(range_components) == 1:
                    hyphenated_components = date_span.text.split("-")
                    if len(hyphenated_components) == 2:
                        range_components = hyphenated_components
                    elif len(hyphenated_components) == 6:
                        # Handle dote ranges like 2015-11-3 - 2015-11-6
                        range_components = [
                            '-'.join(hyphenated_components[:3]),
                            '-'.join(hyphenated_components[3:])]
            if len(range_components) == 1:
                datetime_range = date_to_datetime_range(range_components[0])
                if datetime_range is None:
                    continue
            elif len(range_components) == 2:
                # March 3 to November 2 1984
                datetime_range_a = date_to_datetime_range(range_components[0])
                datetime_range_b = date_to_datetime_range(range_components[1])
                # Reparse dates using eachother as a relative_base incase one of
                # the dates in the date range doesn't include a year component.
                datetime_range_a = date_to_datetime_range(
                        range_components[0],
                        relative_base=(datetime_range_b or [doc.date])[0])
                datetime_range_b = date_to_datetime_range(
                        range_components[1],
                        relative_base=(datetime_range_a or [doc.date])[0])
                if datetime_range_a is None and datetime_range_b is None:
                    continue
                elif datetime_range_a is None:
                    datetime_range = datetime_range_b
                elif datetime_range_b is None:
                    datetime_range = datetime_range_a
                else:
                    # Treat the span's daterange as ending at the start of the
                    # second date component unless a word like "through" is used
                    # with the second component.
                    if re.search(r"\bthrough\b", date_span.text) or\
                       re.search(r"\b(late|end of)\b", range_components[1]):
                        datetime_range = [
                            datetime_range_a[0],
                            datetime_range_b[1]]
                    else:
                        datetime_range = [
                            datetime_range_a[0],
                            datetime_range_b[0]]
            else:
                print("Bad date range split:", date_span.text, range_components)
                continue
            tier_spans.append(DateSpan(date_span, datetime_range))
        return {'dates': AnnoTier(tier_spans)}
