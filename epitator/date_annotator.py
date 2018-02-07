#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier, AnnoSpan
from .annospan import SpanGroup
from .spacy_annotator import SpacyAnnotator
from . import result_aggregators as ra
from dateparser.date import DateDataParser
from dateutil.relativedelta import relativedelta
import re
import datetime

DATE_RANGE_JOINERS = r"to|through|until|untill|and"

ORDINALS = [
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
    "eleventh",
    "twelfth",
    "thirteenth",
    "fourteenth",
    "fifteenth",
    "sixteenth",
    "seventeenth",
    "eighteenth",
    "nineteenth",
    "twentieth",
    "twenty-first",
    "twenty-second",
    "twenty-third",
    "twenty-fourth",
    "twenty-fifth",
    "twenty-sixth",
    "twenty-seventh",
    "twenty-eighth",
    "twenty-ninth",
    "thirtieth",
    "thirty-first",
]
ordinal_date_re = re.compile(
    r"(?P<ordinal>" + "|".join(map(re.escape, ORDINALS)) + ")?"
    r"((?P<ordinal_number>\d{1,2})(st|nd|rd|th))?"
    r" (?P<unit>week|day|month) (of|in)( the (year|month)( of)?)? "
    r"(?P<rest>.{3,})", re.I)
ends_with_timeunit_re = re.compile(r".*(months|days|years)$", re.I)


class DateSpan(AnnoSpan):
    def __init__(self, base_span, datetime_range):
        self.start = base_span.start
        self.end = base_span.end
        self.doc = base_span.doc
        self.label = base_span.doc.text[base_span.start:base_span.end]
        # The date span's datetime range is the time interval represented by
        # the span. The interval ends at the final datetime, and does not
        # include the day, minute or second of the final datetime.
        self.datetime_range = datetime_range

    def __repr__(self):
        return (
            super(DateSpan, self).__repr__() + ':' +
            ' to '.join(x.isoformat().split('T')[0] if x else None
                        for x in self.datetime_range))

    def to_dict(self):
        result = super(DateSpan, self).to_dict()
        result['datetime_range'] = self.datetime_range
        return result


class DateAnnotator(Annotator):
    """
    DateAnnotator annotates and parses dates and date ranges.
    All dates are parsed as datetime ranges. For instance, a date like "11-6-87"
    would be parsed as a range from the start of the day to the end of the day,
    while a month like "December 2011" would be parsed as a range from the start
    of December 1st ending at the start of January 1st 2012.

    Args:
        include_end_date (bool): Indicates whether a date range like "Monday to
        Wednesday" should be parsed as ending at the start of Wednesday
        or the start of Thursday. If a phrase like "Monday through Wednesday"
        is used the date range will extend through Wednesday regardless of
        this argument's value.
    """
    def __init__(self, include_end_date=True):
        self.include_end_date = include_end_date

    def annotate(self, doc):
        doc_date = doc.date or datetime.datetime.now()
        strict_parser = DateDataParser(['en'], settings={
            'STRICT_PARSING': True})

        def clean_date_str(text):
            # strip extra words from the beginning of the date string
            text = re.split(r"(\b(since|from|between)\s)?"
                            r"(^the\s(month|year)\sof\s)?"
                            r"(^the\s)?"
                            r"((beginning|middle|start|end)\sof\s)?"
                            r"((late|mid|early)\s)?", text, re.I)
            text = text[-1]
            # remove extra characters
            text = re.sub(r"\[|\]", "", text)
            return text

        def date_to_datetime_range(text,
                                   relative_base=doc_date,
                                   prefer_dates_from='past'):
            text = clean_date_str(text)
            # Handle ordinal dates like "the second month of 2006"
            match = ordinal_date_re.match(text)
            if match:
                match_dict = match.groupdict()
                if match_dict['ordinal']:
                    ordinal_number = ORDINALS.index(match_dict['ordinal']) + 1
                else:
                    ordinal_number = int(match_dict['ordinal_number'])
                unit = match_dict['unit']
                rest = match_dict['rest']
                if unit == 'day':
                    return date_to_datetime_range(
                        str(ordinal_number) + " " + rest)
                elif unit == 'week':
                    if ordinal_number > 4:
                        return
                    week_start = date_to_datetime_range("1 " + rest)[0]
                    week_start = date_to_datetime_range(
                        "Sunday",
                        # A day is added because if the base date is on Sunday
                        # the prior sunday will be used.
                        relative_base=week_start + relativedelta(days=1))[0]
                    for _ in range(ordinal_number - 1):
                        week_start = date_to_datetime_range(
                            "Sunday",
                            relative_base=week_start + relativedelta(days=1),
                            prefer_dates_from='future')[0]
                    return [
                        week_start,
                        week_start + relativedelta(days=7)]
                elif unit == 'month':
                    month_name = datetime.datetime(2000,
                                                   ordinal_number,
                                                   1).strftime("%B ")
                    return date_to_datetime_range(month_name + rest)
                else:
                    raise Exception("Unknown time unit: " + unit)
            # handle dates like "1950s" since dateparser doesn't
            decade_match = re.match(r"(\d{4})s", text)
            if decade_match:
                decade = int(decade_match.groups()[0])
                return [datetime.datetime(decade, 1, 1),
                        datetime.datetime(decade + 10, 1, 1)]
            parser = DateDataParser(['en'], settings={
                'RELATIVE_BASE': relative_base or datetime.datetime.now(),
                'PREFER_DATES_FROM': prefer_dates_from
            })
            try:
                date_data = parser.get_date_data(text)
            except TypeError:
                return
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

        def parse_non_relative_date(text):
            result = date_to_datetime_range(
                text, relative_base=datetime.datetime(900, 1, 1))
            if result and result[0].year > 1000:
                # If the year is less than 1000 assume the year 900
                # base date was used when parsing so the date is relative.
                return result[0]

        if 'spacy.nes' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        # Create a combine tier of nes and regex dates
        date_span_tier = doc.tiers['spacy.nes'].with_label('DATE')
        # Regex for formatted dates
        regex = re.compile(
            r"\b("
            # date MonthName yyyy
            r"(\d{1,2}\s\w{3,}\s\d{4})|"
            # dd-mm-yyyy
            r"(\d{1,2}\s?[\/\-]\s?\d{1,2}\s?[\/\-]\s?\d{1,4})|"
            # yyyy-MMM-dd
            r"(\d{1,4}\s?[\/\-]\s?\w{3,4}\s?[\/\-]\s?\d{1,4})|"
            # yyyy-mm-dd
            r"(\d{1,4}\s?[\/\-]\s?\d{1,2}\s?[\/\-]\s?\d{1,2})"
            # Negative lookahead to prevent matches on other types of slash
            # separated data.
            r")\b(?!\s?[\/\-]\s?\d{1,})", re.I)
        match_tier = doc.create_regex_tier(regex)
        date_span_tier += match_tier
        # Group adjacent date info in case it is parsed as separate chunks.
        # ex: Friday, October 7th 2010.
        adjacent_date_spans = date_span_tier.combined_adjacent_spans(max_dist=9)
        grouped_date_spans = []

        def is_individually_parsable(text):
            try:
                return strict_parser.get_date_data(text)['date_obj'] is not None
            except TypeError:
                return False
        for date_group in adjacent_date_spans:
            date_group_spans = list(date_group.iterate_leaf_base_spans())
            if any(not is_individually_parsable(span.text) for span in date_group_spans):
                if date_to_datetime_range(date_group.text) is not None:
                    grouped_date_spans.append(date_group)
        # Find date ranges by looking for joiner words between dates.
        date_range_spans = ra.label('date_range',
                                    date_span_tier.with_following_spans_from(
                                        [t_span for t_span in doc.tiers['spacy.tokens']
                                         if re.match(r"(" + DATE_RANGE_JOINERS + r"|\-)$",
                                                     t_span.text,
                                                     re.I)]).with_following_spans_from(date_span_tier))
        since_tokens = AnnoTier(ra.label('since_token', [
            t_span for t_span in doc.tiers['spacy.tokens']
            if 'since' == t_span.token.lemma_]), presorted=True)
        since_date_spans = ra.label(
            'since_date',
            since_tokens.with_following_spans_from(date_span_tier, allow_overlap=True) +
            date_span_tier.with_contained_spans_from(since_tokens))
        tier_spans = []
        all_date_spans = AnnoTier(
            date_range_spans +
            grouped_date_spans +
            date_span_tier.spans +
            since_date_spans)
        all_date_spans = all_date_spans.optimal_span_set(prefer='text_length')
        for date_span in all_date_spans:
            # Parse the span text into one or two components depending on
            # whether it contains multiple dates for specifying a range.
            if_span_group = isinstance(date_span, SpanGroup)
            if if_span_group and date_span.label == 'date_range':
                range_components = [span.text
                                    for span in date_span.base_spans[0::2]]
            else:
                range_components = re.split(r"\b(?:" + DATE_RANGE_JOINERS + r")\b",
                                            date_span.text,
                                            re.I)
                if len(range_components) == 1:
                    hyphenated_components = date_span.text.split("-")
                    if len(hyphenated_components) == 2:
                        range_components = hyphenated_components
                    elif len(hyphenated_components) == 6:
                        # Handle dote ranges like 2015-11-3 - 2015-11-6
                        range_components = [
                            '-'.join(hyphenated_components[:3]),
                            '-'.join(hyphenated_components[3:])]
            if ends_with_timeunit_re.match(range_components[-1]):
                # Prevent durations like "5 days" from being parsed as specific
                # dates like "5 days ago"
                continue
            elif len(range_components) == 1:
                if date_span.label == 'since_date':
                    date_str = [span for span in date_span.base_spans
                                if span.label != 'since_token'][0].text
                    datetime_range = date_to_datetime_range(date_str)
                    if datetime_range is None:
                        continue
                    datetime_range = [datetime_range[0], doc_date]
                else:
                    date_str = range_components[0]
                    datetime_range = date_to_datetime_range(date_str)
                    if datetime_range is None:
                        continue
            elif len(range_components) == 2:
                # Check for a non-relative date in the range that can be used as
                # a relative base date the other date.
                # Example: March 3 to November 2 1984
                non_relative_dates = [
                    parse_non_relative_date(text)
                    for text in range_components]
                relative_base_date = next((x for x in non_relative_dates if x),
                                          doc_date)
                datetime_range_a = date_to_datetime_range(
                    range_components[0],
                    relative_base=relative_base_date)
                datetime_range_b = date_to_datetime_range(
                    range_components[1],
                    relative_base=relative_base_date)
                if datetime_range_a is None and datetime_range_b is None:
                    continue
                elif datetime_range_a is None:
                    datetime_range = datetime_range_b
                elif datetime_range_b is None:
                    datetime_range = datetime_range_a
                else:
                    # If include_end_date is False treat the span's daterange
                    # as ending at the start of the second date component unless
                    # a word like "through" is used in the second component.
                    if self.include_end_date or\
                       re.search(r"\bthrough\b", date_span.text) or\
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
            # Omit reverse ranges because they usually come from something
            # being incorrectly parsed. The main exception is relative dates
            # like 2 to 3 weeks ago.
            if datetime_range[0] <= datetime_range[1]:
                tier_spans.append(DateSpan(date_span, datetime_range))
        return {'dates': AnnoTier(tier_spans, presorted=True)}
