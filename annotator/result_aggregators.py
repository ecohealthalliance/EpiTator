#!/usr/bin/env python
"""
Pattern search result aggregation functions.
These functions allow you to build up meta-queries out of
pattern.search subqueries.
"""
import pattern, pattern.search
import itertools
import maximum_weight_interval_set as mwis
class MetaMatch(pattern.search.Match):
    """
    A match composed of pattern Matches
    """
    def __init__(self, matches, labels):
        self.matches = matches
        self.labels = labels
        min_idx = min([m.words[0].abs_index for m in matches])
        max_idx = max([m.words[-1].abs_index for m in matches])
        self.words = matches[0].words[0].doc_word_array[min_idx:max_idx + 1]
    def __repr__(self):
        return "MetaMatch(" + ", ".join(map(str, self.matches)) + ")"
    def groupdict(self):
        """
        Return a dict with all the labeled matches.
        """
        out = {}
        for label, match in zip(self.labels, self.matches):
            if label != None:
                out[label] = match
            if isinstance(match, MetaMatch):
                if label:
                    out[label] = match.groupdict()
                else:
                    out.update(match.groupdict())
        return out

    def interate_matches(self):
        """
        Iterate over all the plain match objects nested in MetaMatches
        """
        for match in self.matches:
            if isinstance(match, MetaMatch):
                for match2 in match.matches:
                    yield match2
            else:
                yield match
    def match_length(self, include_overlap=False):
        """
        Return the cumulative length of all the submatches rather than the
        length of the meta match's span including space between submatches
        (which len() would return).
        """
        word_indices = {}
        for match in self.interate_matches():
            for word in match.words:
                word_indices[word.index] = word_indices.get(word.index, 0) + 1
        if include_overlap:
            return sum(word_indices.values())
        else:
            return len(word_indices)
    def constituents(self):
        return self.words

def near(results_lists, max_words_between=30):
    """
    Returns matches from mulitple results lists that appear in the same sentence
    within the given proximity.
    I.e. outer join of the results lists where at least two elements are not
    null, the elements have the same sentence, and no element is more than
    n words away from all other elements in the tuple
    """
    result = []
    non_empty_lists = [
        rl for rl in results_lists
        if (isinstance(rl, list) and len(rl) > 0) or
           (isinstance(rl, tuple) and len(rl[1]) > 0)
    ]
    for i in range(2, len(non_empty_lists) + 1):
        for permutation in itertools.permutations(non_empty_lists, i):
            result += follows(permutation, max_words_between, max_overlap=10)
    return result

def match_follows(match_a, match_b, max_words_between, max_overlap):
    """
    Returns true if the second match is in the same sentence,
    ends after the first begins,
    doesn't start more than max_words_between away from the first match and
    doesn't begin more than max_overlap before the end of the first match.
    """
    if match_a.words[-1].sentence != match_b.words[0].sentence:
        return False
    match_a_start = match_a.words[0].index
    match_a_end = match_a.words[-1].index
    match_b_start = match_b.words[0].index
    match_b_end = match_b.words[-1].index
    if match_b_end < match_a_start:
        return False
    words_between = match_b_start - match_a_end - 1
    if (-words_between) > max_overlap:
        return False
    if words_between > max_words_between:
        return False
    return True

def follows(results_lists, max_words_between=0, max_overlap=5):
    """
    Find sequences of matches matching the order in the results lists.
    The max_words_between parameter sets how far apart the matches can appear
    in a sequence.
    Results are considered to follow eachother so long as the first match
    starts before the second ends. This is the weakest definition of following.
    A stronger definition can be used by limiting the max_overlap.
    Sequences must appear in the same sentence. We could try to remove this
    contraint by adding sentence indecies to matches, but I don't think
    that would be very useful.
    """
    sequences = [[]]
    for results in results_lists:
        if isinstance(results, tuple):
            # Tuples are syntactic sugar for labeled result lists.
            results = results[1]
        next_sequences = []
        for result in results:
            for sequence in sequences:
                if len(result.words) == 0:
                    raise Exception(str(result) + "," +  str(results))
                if (
                    len(sequence) == 0 or
                    match_follows(
                        sequence[-1], result, max_words_between, max_overlap
                    )
                ):
                    next_sequences.append(sequence + [result])
        sequences = next_sequences
    labels = [
        r[0] if isinstance(r, tuple) else None
        for r in results_lists
    ]
    return [MetaMatch(seq, labels) for seq in sequences]

def label(label, results_list):
    """
    Attach a label to the results list so it can be looked up in a meta
    match object via groupdict.
    """
    return follows([(label, results_list)])

def combine(
    results_lists,
    prefer="first",
    max_proximity=0,
    remove_conflicts=False
):
    """
    Combine the results_lists while removing overlapping matches.

    if matches are within max_proximity of eachother they are considered
    overlapping
    
    remove_conflicts removes all results that overlap rather than keeping one.
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
        return len(x.string)
    def match_length(x, include_overlap=False):
        """
        Prefers the match with the most text that matches the submatch patterns.
        """
        if isinstance(x, MetaMatch):
            return x.match_length(include_overlap)
        else:
            return len(x)
    if prefer == "first":
        prefunc = first
    elif prefer == "text_length":
        prefunc = text_length
    elif prefer == "match_length":
        prefunc = match_length
    else:
        prefunc = prefer
    if not remove_conflicts:
        my_mwis = mwis.find_maximum_weight_interval_set([
            mwis.Interval(
                start=match.words[0].abs_index,
                end=match.words[-1].abs_index,
                weight=prefunc(match),
                corresponding_object=match
            )
            for match in all_results
        ])
        return [
            interval.corresponding_object
            for interval in my_mwis
        ]
    else:
        remaining_results = all_results
        out_results = []
        while len(remaining_results) > 0:
            match_a = remaining_results.pop(0)
            overlaps = []
            for match_b in remaining_results:
                if match_a.words[0].sentence != match_b.words[0].sentence: continue
                a_start, a_end = match_a.words[0].index, match_a.words[-1].index
                b_start, b_end = match_b.words[0].index, match_b.words[-1].index
                if (
                    (
                        a_start + max_proximity >= b_start and
                        a_start - max_proximity <= b_end
                    ) or (
                        b_start + max_proximity >= a_start and
                        b_start - max_proximity <= a_end
                    )
                ):
                    overlaps.append(match_b)
            if len(overlaps) == 0:
                out_results.append(match_a)
            else:
                for overlap in overlaps:
                    if overlap in remaining_results:
                        remaining_results.remove(overlap)
        return out_results

class Chain():
    def __init__(self, results_lists):
        self.results_lists = results_lists
    def follows(self, **kwargs):
        self.results_lists = [follows(self.results_lists, **kwargs)]
        return self
    def combine(self, **kwargs):
        self.results_lists = [combine(self.results_lists, **kwargs)]
        return self
