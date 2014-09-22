#!/usr/bin/env python
"""Classes to hold time-related objects"""

class TimePoint:

    def __init__(self, iso_string=None, year=None, month=None, date=None,
                 hour=None, minute=None, second=None, mod=None):
        self.year = year
        self.month = month
        self.date = date
        self.hour = hour
        self.minute = minute
        self.second = second
        self.mod = mod

    def __repr__(self):
        return ' '.join(['year:', str(self.year), 'month:', str(self.month),
                         'date:', str(self.date), 'hour:', str(self.hour),
                         'minute:', str(self.minute), 'second:', str(self.second),
                         'mod:', str(self.mod)])

    def to_dict(self):
        return dict( (key, val)
                     for key, val in self.__dict__.iteritems()
                     if val is not None)


    @staticmethod
    def from_json(json):
        """Build a TimePoint from a JSON object"""
        return TimePoint(**json)


class TimeRange:

    def __init__(self, begin, end, mod=None):
        self.begin = begin
        self.end = end
        self.mod = mod

    def to_dict(self):
        return dict( (key, val)
                     for key, val in self.__dict__.iteritems()
                     if val is not None)

    @staticmethod
    def from_json(json):
        """Build a TimeRange from a JSON object"""
        begin = TimePoint.from_json(json['begin'])
        end = TimePoint.from_json(json['end'])
        mod = json['mod'] if 'mod' in json else None
        return TimeRange(begin, end, mod)

class TimeDuration:

    def __init__(self, label, mod=None):
        self.label = label
        self.mod = mod

    def __repr__(self):
        return ' '.join(['label:', str(self.label), 'mod:', str(self.mod)])

    def to_dict(self):
        return dict( (key, val)
                     for key, val in self.__dict__.iteritems()
                     if val is not None)

    @staticmethod
    def from_json(json):
        """Build a TimeDuration from a JSON object"""
        return TimeDuration(**json)

class TimeSet:

    def __init__(self, label, mod=None):
        self.label = label
        self.mod = mod

    def __repr__(self):
        return ' '.join(['label:', str(self.label), 'mod:', str(self.mod)])

    def to_dict(self):
        return dict( (key, val)
                     for key, val in self.__dict__.iteritems()
                     if val is not None)


    @staticmethod
    def from_json(json):
        """Build a TimeSet from a JSON object"""
        return TimeSet(**json)
