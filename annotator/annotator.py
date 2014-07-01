#!/usr/bin/env python
"""Annotator"""

from lazy import lazy

from nltk import sent_tokenize

def tokenize(text):
	return sent_tokenize(text)

class Annotator:

	def annotate():
		"""Take some input, possibly a raw string or Unicode object, or and
		    annotation tier, and produce a new annotation tier."""
		raise NotImplementedError("annotate method must be overridden in child")

class AnnoDoc:

	# TODO what if the original text needs to be later transformed, e.g.
	# stripped of tags?

	def __init__(self, text=None):
		if text:
			raw_sentences = sent_tokenize(text)
			self.sentences = [AnnoSentence(raw_sentence)
			                  for raw_sentence in raw_sentences]


class AnnoSentence:

	# TDOD should we store sentence start and stop offets?

	def __init__(self, text, tiers=None):
		self.text = text
		if tiers is None:
			self.tiers = {}
		else:
			self.tiers = tiers

	def __repr__(self):
		return 'text: {0} tiers: {1}'.format(self.text, self.tiers)

class AnnoTier:

	def __init__(self, spans=None):
		if spans is None:
			self.spans = []
		else:
			self.spans = spans
			

	def __repr__(self):
		return str([str(span) for span in self.spans])

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

	def spans_at(self, start, size):
		"""Get all spans with certain start and end positions"""
		return filter(lambda span: start == span.start and size == span.size,
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

class AnnoSpan:

	def __repr__(self):
		return '{0}-{1}:{2}'.format(self.start, self.end, self.text)

	def __init__(self, start, end, sentence, label=None):
		self.start = start
		self.end = end
		self.size = start - end
		if label != None:
			self.label = label
		else:
			self.label = sentence.text[start:end]
		self.sentence = sentence

	@lazy
	def text(self):
		return self.sentence.text[self.start:self.end]


