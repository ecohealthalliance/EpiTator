#!/usr/bin/env python
import itertools
import maximum_weight_interval_set as mwis
from annotator import AnnoSpan

class MatchSpan(AnnoSpan):
    def __init__(self, base_spans, match_name=None):
        if isinstance(base_spans, AnnoSpan):
            base_spans = [base_spans]
        self.base_spans = base_spans
        assert len(base_spans) > 0
        self.start = min([s.start for s in base_spans])
        self.end = max([s.end for s in base_spans])
        self.doc = base_spans[0].doc
        self.label = self.text
        self.match_name = match_name
    def __repr__(self):
        match_name = ""
        if self.match_name:
            match_name = self.match_name + ", "
        return "MatchSpan(" + match_name + ", ".join(map(str, self.base_spans)) + ")"
    def groupdict(self):
        """
        Return a dict with all the labeled matches.
        """
        out = {}
        for base_span in self.base_spans:
            if isinstance(base_span, MatchSpan):
                out.update(base_span.groupdict())
        if self.match_name:
            out[self.match_name] = self
        return out
    def iterate_base_spans(self):
        """
        Recursively iterate over all base_spans including base_spans of child MatchSpans.
        """
        for span in self.base_spans:
            yield span
            if isinstance(span, MatchSpan):
                for span2 in span.iterate_base_spans():
                    yield span2

    def iterate_leaf_base_spans(self):
        """
        Return the leaf base spans in the MatchSpan tree.
        """
        for span in self.iterate_base_spans():
            if not isinstance(span, MatchSpan):
                yield span

def near(results_lists, max_dist=100, allow_overlap=True):
    """
    Returns matches from mulitple results lists that appear within the given proximity.
    """
    result = []
    for permutation in itertools.permutations(results_lists):
        result += follows(permutation, max_dist, allow_overlap)
    return result

def follows(results_lists, max_dist=100, allow_overlap=False):
    """
    Find sequences of matches within the given proximity that occur in the same
    order as the results lists.
    """
    sequences = []
    for idx, results in enumerate(results_lists):
        if len(results) == 0:
            return []
        if idx == 0:
            sequences = [[r] for r in results]
            continue
        next_sequences = []
        for result in results:
            for sequence in sequences:
                if sequence[-1].comes_before(result,
                    max_dist=max_dist, allow_overlap=allow_overlap):
                    next_sequences.append(sequence + [result])
        sequences = next_sequences
    return [MatchSpan(seq) for seq in sequences]

def label(label, results_list):
    """
    Attach a label to the results so it can be looked up in a via groupdict.
    """
    return [MatchSpan(match, label) for match in results_list]

def combine(results_lists, prefer="first"):
    """
    Combine the results_lists while removing overlapping matches.
    """
    all_results = reduce(lambda sofar, k: sofar + k, results_lists, [])
    def first(x):
        """
        Perfers the matches that appear first in the first result list.
        """
        return len(all_results) - all_results.index(x)
    def text_length(x):
        """
        Prefers the match with the longest span of text that contains all the
        matching content.
        """
        return len(x)
    def num_spans(x):
        """
        Prefers the match with the most distinct base spans.
        """
        if isinstance(x, MatchSpan):
            return len(set(x.iterate_leaf_base_spans()))
        else:
            return 1
    if prefer == "first":
        prefunc = first
    elif prefer == "text_length":
        prefunc = text_length
    elif prefer == "num_spans":
        prefunc = num_spans
    else:
        prefunc = prefer
    my_mwis = mwis.find_maximum_weight_interval_set([
        mwis.Interval(
            start=match.start,
            end=match.end,
            weight=prefunc(match),
            corresponding_object=match
        )
        for match in all_results
    ])
    return [
        interval.corresponding_object
        for interval in my_mwis
    ]

def remove_overlaps(list_a, list_b):
    """
    Return a verion of list_a with the items that overlap items in list_b removed.
    """
    list_a = sorted(list_a)
    list_b = sorted(list_b)
    out = list()
    idx_a = 0
    idx_b = 0
    if len(list_a) == 0 or len(list_b) == 0:
        return list_a
    while True:
        # Advance the list_b pointer to the first span ahead of the list_a's
        # while sequentially checking for overlaps in the list_b spans
        # with the current list_a span. If an overlap is found advance
        # the list_a pointer so it is not included in the output.
        while list_a[idx_a].end > list_b[idx_b].start:
            if list_a[idx_a].overlaps(list_b[idx_b]):
                idx_a += 1
                if idx_a == len(list_a):
                    return out
            else:
                idx_b += 1
                if idx_b == len(list_b):
                    return out + list_a[idx_a:]
        # While list_b pointer is pointed at the first span ahead of list_a's
        # add the list_a spans to the output.
        while list_a[idx_a].end <= list_b[idx_b].start:
            out.append(list_a[idx_a])
            idx_a += 1
            if idx_a == len(list_a):
                return out
