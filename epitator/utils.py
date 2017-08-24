#!/usr/bin/env python
from __future__ import absolute_import
import re

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
        # Sometimes spacy CARDIAL entities will include descriptors like
        # about, or more than.
        if t in ['about', 'less', 'more', 'than']:
            continue
        t = punctuation.sub('', t)
        t = affix.sub(r'\1', t)
        cleaned_tokens.append(t.lower())
    if len(cleaned_tokens) == 0:
        return None
    totals = [0]
    for t in cleaned_tokens:
        number = parse_number(t)
        if number is not None:
            totals[-1] = number
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
            return None
    return sum(totals)


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
