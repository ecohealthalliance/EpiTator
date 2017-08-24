#!/usr/bin/env python
# coding=utf8
"""Annotator"""
from __future__ import absolute_import
from __future__ import print_function
from .annodoc import AnnoDoc
from .annospan import AnnoSpan
from .annotier import AnnoTier

class Annotator(object):

    def annotate(self, doc):
        """Take an AnnoDoc and produce a new annotation tier"""
        raise NotImplementedError(
            "annotate method must be implemented in child")
