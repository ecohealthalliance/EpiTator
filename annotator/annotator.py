#!/usr/bin/env python
"""Annotator"""

from lazy import lazy

from nltk import sent_tokenize

def tokenize(text):
	return sent_tokenize(text)

class Annotator:

	def annotate():
		"""Take an AnnoDoc and produce a new annotation tier"""
		raise NotImplementedError("annotate method must be implemented in child")

class AnnoDoc:

	# TODO what if the original text needs to be later transformed, e.g.
	# stripped of tags? This will ruin offsets.

	def __init__(self, text=None):
		self.text = text
		self.tiers = {}

	def add_tier(self, annotator):
		annotator.annotate(self)

class AnnoTier:

	def __init__(self, spans=None):
		if spans is None:
			self.spans = []
		else:
			self.spans = spans

	def __repr__(self):
		return unicode([unicode(span) for span in self.spans])

	def spans_over(self, start, end=None):
		"""Get all spans which overlap a position or range"""
		if not end: end = start + 1
		return filter(lambda span: len(set(range(span.start, span.end)).
				                       intersection(range(start, end))) > 0,
					  self.spans)

	def spans_in(self, start, end):
		"""Get all spans which are contained in a range"""
		return filter(lambda span: span.start >= start and span.end <= end,
			          self.spans)

	def spans_at(self, start, end):
		"""Get all spans with certain start and end positions"""
		return filter(lambda span: start == span.start and end == span.end,
			          self.spans)

	def spans_over_span(self, span):
		"""Get all spans which overlap another span"""
		self.spans_over(span.start, span.end)

	def spans_in_span(self, span):
		"""Get all spans which lie within a span"""
		self.spans_in(span.start, span.end)

	def spans_at_span(self, span):
		"""Get all spans which have the same start and end as another span"""
		self.spans_at(span.start, span.end)

	def spans_with_label(self, label):
		"""Get all spans which have a given label"""
		filter(lambda span: span.label == label, self.spans)

	def labels(self):
		"""Get a list of all labels in this tier"""
		return [span.label for span in self.spans]

class AnnoSpan:

	def __repr__(self):
		return u'{0}-{1}:{2}'.format(self.start, self.end, self.text)

	def __init__(self, start, end, doc, label=None):
		self.start = start
		self.end = end
		self.doc = doc

		if label == None:
			self.label = self.text
		else:
			self.label = label
	
	def size(self): return self.end - self.start

	@lazy
	def text(self):
		return self.doc.text[self.start:self.end]


