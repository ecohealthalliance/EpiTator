#!/usr/bin/env python
"""
Pattern search result aggregation functions.
These functions allow you to build up meta-queries out of
pattern.search subqueries.
"""
import pattern
import itertools
class MetaMatch(pattern.search.Match):
    """
    A match composed of pattern Matches
    """
    def __init__(self, matches, labels):
        self.matches = matches
        self.labels = labels
        min_idx = min([m.words[0].index for m in matches])
        max_idx = max([m.words[-1].index for m in matches])
        self.words = matches[0].words[-1].sentence.words[min_idx:max_idx + 1]

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
    
    def match_length(self):
        """
        Return the cumulative length of all the submatches rather than the
        length of the meta match's span including space between submatches
        (which len() would return).
        """
        return sum([
            m.match_length() if isinstance(m, MetaMatch) else len(m)
            for m in self.matches
        ])

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
    for permutation in itertools.permutations(results_lists):
        result += follows(permutation, max_words_between)
    return result

def match_follows(match_a, match_b, max_words_between):
    """
    Returns true if the second match comes after the first
    and is in the same sentence.
    """
    if match_a.words[-1].sentence != match_b.words[0].sentence:
        return False
    word_a_idx = match_a.words[-1].index
    word_b_idx = match_b.words[0].index
    if word_a_idx < word_b_idx:
        if word_a_idx + max_words_between + 1 >= word_b_idx:
            return True
    return False

def follows(results_lists, max_words_between=0):
    """
    Find sequences of matches matching the order in the results lists.
    The max_words_between parameter sets how far apart the matches can appear
    in a sequence.
    Sequences must appear in the same sentence. We could try to remove this
    contraint by adding sentence indecies to matches, but I don't think
    that would be very useful.
    """
    sequences = [[]]
    for results in results_lists:
        if isinstance(results, tuple):
            results = results[1]
        next_sequences = []
        for result in results:
            for sequence in sequences:
                if (
                    len(sequence) == 0 or
                    match_follows(sequence[-1], result, max_words_between)
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

def combine(results_lists, prefer="first"):
    """
    Combine the results_lists while removing overlapping matches.
    """
    def first(a,b):
        """
        This perference function perfers the matches that appear first 
        in the first result list.
        """
        return True
    def longer_text(a,b):
        """
        Prefers the match with the longest span of text that contains all the
        matching content.
        """
        return len(a.string) >= len(b.string)
    def longer_match(a,b):
        """
        Prefers the match with the most text that matches the submatch patterns.
        """
        a_len, b_len = len(a), len(b)
        if isinstance(a, MetaMatch):
            a_len = a.match_length()
        elif isinstance(b, MetaMatch):
            b_len = b.match_length()
        else:
            return a_len >= b_len
    if prefer == "first":
        prefunc = first
    elif prefer == "longer_text":
        prefunc = longer_text
    elif prefer == "longer_match":
        prefunc = longer_match
    else:
        prefunc = prefer
    
    results_a = results_lists[0]
    if len(results_lists) < 2:
        results_b = []
    elif len(results_lists) > 2:
        results_b = combine(results_lists[1:], prefer)
    else:
        results_b = results_lists[1]
    
    remaining_results = results_a + results_b
    out_results = []
    while len(remaining_results) > 0:
        match_a = remaining_results.pop(0)
        keep_a = True
        overlaps = []
        for match_b in remaining_results:
            if match_a.words[0].sentence != match_b.words[0].sentence: continue
            a_start, a_end = match_a.words[0].index, match_a.words[-1].index
            b_start, b_end = match_b.words[0].index, match_b.words[-1].index
            if (
                (a_start >= b_start and a_start <= b_end) or
                (b_start >= a_start and b_start <= a_end)
            ):
                if not prefunc(match_a, match_b):
                    keep_a = False
                    break
                else:
                    overlaps.append(match_b)
        if keep_a:
            if match_a not in out_results:
                out_results.append(match_a)
            for overlap in overlaps:
                if overlap in remaining_results:
                    remaining_results.remove(overlap)
    return out_results
