#!/usr/bin/env python
from __future__ import absolute_import
import itertools
from . import maximum_weight_interval_set as mwis
from .annospan import SpanGroup
from six.moves import map
from functools import reduce


def near(results_lists, max_dist=100, allow_overlap=True):
    """
    Returns matches from mulitple results lists that appear within the given proximity.
    """
    result = []
    for permutation in itertools.permutations(results_lists):
        result += follows(permutation, max_dist, allow_overlap)
    return result


def follows(results_lists, max_dist=1, allow_overlap=False, label=None):
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
    return [SpanGroup(seq, label) for seq in sequences]


def label(label, results_list):
    """
    Attach a label to the results so it can be looked up in a via groupdict.
    """
    return [SpanGroup([match], label) for match in results_list]


def combine(results_lists, prefer="first"):
    """
    Combine the results_lists while removing overlapping matches.
    """
    all_results = reduce(lambda sofar, k: sofar + k, results_lists, [])

    def first(x):
        """
        Perfers the matches that appear first in the first result list.
        """
        # Using an exponent makes it so that a first match will be prefered
        # over multiple non-overlapping later matches.
        return 2 ** (len(all_results) - all_results.index(x))

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
        if isinstance(x, SpanGroup):
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
