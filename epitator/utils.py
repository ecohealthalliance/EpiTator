#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
import re
from collections import defaultdict
from itertools import compress

NUMBERS = {
    'zero': 0,
    'half': 1.0 / 2.0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90,
}
ORDERS = {
    'hundred': 100,
    'thousand': 1000,
    'million': 1000000,
    'billion': 1000000000,
    'trillion': 1000000000000,
    'gillion': 1000000000,
}


def parse_number(num, default=None):
    try:
        return int(num)
    except ValueError:
        try:
            return float(num)
        except ValueError:
            return default


def parse_spelled_number(num_str):
    """Parse spelled out whole numbers."""
    tokens = []
    for t in num_str.strip().split(' '):
        if len(t) > 0:
            tokens.extend(t.split('-'))
    punctuation = re.compile(r'[\,\(\)]')
    affix = re.compile(r'(\d+)(st|nd|rd|th)')
    cleaned_tokens = []
    for t in tokens:
        if t == 'and':
            continue
        t = punctuation.sub('', t)
        t = affix.sub(r'\1', t)
        cleaned_tokens.append(t.lower())
    if len(cleaned_tokens) == 0:
        return None
    totals = [0]
    numeric_tokens_found = False
    prev_digits = False
    for t in cleaned_tokens:
        number = parse_number(t)
        if number is not None:
            if prev_digits:
                totals[-1] = totals[-1] * 1000 + number
            else:
                totals[-1] += number
        elif t in NUMBERS:
            # Ex: twenty one
            totals[-1] += NUMBERS[t]
        elif t in ORDERS:
            # if order is greater than previous order it should be combined.
            # Ex: five hundrend three thousand
            if len(totals) > 1 and ORDERS[t] > totals[-2]:
                totals[-2] = sum(totals[-2:]) * ORDERS[t]
                totals[-1] = 0
            else:
                totals[-1] *= ORDERS[t]
                totals.append(0)
        else:
            # Sometimes spacy number entities will include words like
            # about, or more than. This allows the initial tokens to be
            # skipped if they can't be parsed as numbers.
            if numeric_tokens_found:
                return None
            else:
                continue
        prev_digits = number is not None
        numeric_tokens_found = True
    if numeric_tokens_found:
        return sum(totals)


def parse_count_text(count_text, verbose=False):
    # verboseprint = print if verbose else lambda *a, **k: None
    if count_text[0] == '0' and len(count_text) > 1:
        return
    try:
        count = int(count_text)
    except ValueError:
        pass  # Try to parse it as a float
    try:
        count = parse_spelled_number(count_text)
    except ValueError:
        pass
    if count is None or int(count) != count:
        return
    else:
        return(count)


def batched(iterable, batch_size=100):
    """
    Sequentially yield segments of the iterable in lists of the given size.
    """
    batch = []
    for idx, item in enumerate(iterable):
        batch.append(item)
        batch_idx = idx % batch_size
        if batch_idx == batch_size - 1:
            yield batch
            batch = []
    yield batch


def flatten(l, unique=False, simplify=False):
    """
    Flatten an arbitrarily deep list or set to a depth-one list.

    simplify -- If the function would return a length-one list, instead
    returns the contents of that list (default False).

    unique -- Removes duplicate values (default False).
    """
    out = []
    for item in l:
        if isinstance(item, (list, tuple)):
            out.extend(flatten(item))
        else:
            out.append(item)
    if unique is True:
        out = list(set(out))
    if simplify is True:
        if len(out) == 0:
            return None
        if len(out) == 1:
            return(out[0])
        else:
            pass
    return out


def merge_dicts(dicts, unique=False, simplify=None):
    """
    Merge a list of dictionaries, returning a single dictionary with combined
    values from all dictionaries in the list.

    The arguments simplify and unique may be supplied as booleans or lists of
    key names. If booleans, they apply to all keys in the dictionary. If lists
    of key names, they are taken to be True for those keys, and False for all
    others.

    unique -- Removes duplicate values (default False).

    simplify -- If the function would return a length-one list, instead
    returns the contents of that list (default None). If simplify is None, the
    function will attempt to be smart, behaving as follows. If there is more
    than one item for a key, that key's value in the merged dict will be a
    list. If only one unique value is to be returned, it will be returned as a
    list if the input dict's value is stored as a list, otherwise it will be
    simplified.
    """
    if not isinstance(dicts, list):
        raise ValueError("first argument must be a list of dicts")

    merged_dicts = defaultdict(list)

    for d in dicts:
        for key, value in d.items():
            merged_dicts[key].append(value)

    for key, value in merged_dicts.items():
        u_arg = unique if isinstance(unique, bool) else (key in unique)

        if simplify is None:
            has_key = [key in d.keys() for d in dicts]
            values = [d[key] for d in compress(dicts, has_key)]
            s_arg = any([not isinstance(v, list) for v in values])
        elif isinstance(simplify, bool):
            s_arg = simplify
        else:
            (key in simplify)

        merged_dicts[key] = flatten(value, simplify=s_arg, unique=u_arg)

    return(dict(merged_dicts))


def verboseprint(verbose=False, *args, **kwargs):
    print(*args, **kwargs) if verbose else lambda *args, **kwargs: None
