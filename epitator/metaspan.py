from .annospan import AnnoSpan
from .utils import flatten, merge_dicts


class MetaSpan(AnnoSpan):
    def __init__(self, span=None, start=None, end=None, doc=None, metadata={}):
        if span is None:
            self.start = start
            self.end = end
            self.doc = doc
        elif isinstance(span, AnnoSpan):
            self.start = span.start
            self.end = span.end
            self.doc = span.doc
        else:  # We assume that span is a spaCy token
            self.start = span.idx
            self.end = span.idx + len(span)
            self.token = span
            self.doc = doc
        self.label = self.text
        self._metadata = span.metadata if isinstance(span, MetaSpan) else metadata

    def __repr__(self):
        return "MetaSpan(start={}, end={}, doc={}, metadata={})".format(self.start,
                                                                        self.end,
                                                                        self.doc,
                                                                        self.metadata)

    def __str__(self):
        return "{}-{}: '{}' {}".format(self.start, self.end, self.text, self.metadata)

    def to_dict(self):
        result = super(MetaSpan, self).to_dict()
        result.update(self.metadata)
        result['text'] = self.text
        return result

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    @metadata.deleter
    def metadata(self):
        del self._metadata

    def update_metadata(self, metagen, *args, **kwargs):
        result = metagen.generate(self, *args, **kwargs)
        if isinstance(result, dict):
                self._metadata = merge_dicts([result, self._metadata], unique=True)
        return self.metadata

    @property
    def tokens(self):
        tokens_tier = self.doc.tiers["spacy.tokens"]
        tokens = [t.token for t in tokens_tier.spans_contained_by_span(self)]
        return(tokens)


class MetaGroup(MetaSpan, SpanGroup):
    def __init__(self, base_spans, label=None):
        assert isinstance(base_spans, list)
        assert len(base_spans) > 0
        self.base_spans = [MetaSpan(span) for span in base_spans]
        self.doc = base_spans[0].doc
        self._label = label
        self._metadata = {}

    def __repr__(self):
        return "MetaGroup(start={}, end={}, doc={}, metadata={})".format(self.start,
                                                                         self.end,
                                                                         self.doc,
                                                                         self.metadata)

    def __str__(self):
        text = "merged text and metadata:\n    {}-{}: '{}'\n    {}".format(self.start,
                                                                           self.end,
                                                                           self.text,
                                                                           self.metadata)
        text += "\ngroup metadata:\n    {}".format(self._metadata)
        text += "\nbase text and metadata:"
        for span in self.iterate_base_spans():
            text += "\n    {}-{}: '{}' {}".format(span.start,
                                                  span.end,
                                                  span.text,
                                                  span.metadata)
        return(text)

    def __iter__(self):
        return(iter(flatten(self.base_spans)))

#     def __next__(self):
#         for span in flatten(self.base_spans):
#             return span
#         raise StopIteration

    @property
    def start(self):
        return(min([s.start for s in self.base_spans]))

    @property
    def end(self):
        return(max([s.end for s in self.base_spans]))

    @property
    def text(self):
        return self.doc.text[self.start:self.end]

    @property
    def label(self):
        if self._label is None:
            return(self.text)
        else:
            return(self._label)

    @property
    def metadata(self, **kwargs):
        metadata_list = [self._metadata] + [s.metadata for s in self.iterate_base_spans()]
        metadata = merge_dicts(metadata_list, unique=True, **kwargs)
        return(metadata)

    def update_group_metadata(self, metagen, *args, **kwargs):
        result = metagen.generate(self, *args, **kwargs)
        if isinstance(result, dict):
                self._metadata = merge_dicts([result, self._metadata], unique=True)
        return self.metadata

    def update_base_span_metadata(self, metagen, *args, **kwargs):
        for span in self.iterate_base_spans():
            span.update_metadata(metagen, *args, **kwargs)
        return self.metadata

    # I could be convinced that either way is better on this.
    def update_metadata(self, metagen, *args, **kwargs):
        self.update_base_span_metadata(metagen, *args, **kwargs)
        # self.update_group_metadata(metagen, *args, **kwargs)

    @property
    def tokens(self):
        tokens_tier = self.doc.tiers["spacy.tokens"]
        tokens = []
        for span in self.iterate_base_spans():
            tokens.append([t.token for t in tokens_tier.spans_contained_by_span(span)])
        tokens = flatten(tokens)
        return(tokens)

    def append(self, spans):
        if isinstance(spans, AnnoSpan):
            self.base_spans.append(spans)
        elif isinstance(spans, list):
            self.base_spans.extend(spans)
