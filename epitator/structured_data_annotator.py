#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier, AnnoSpan
import re
import pyparsing as pypar


def word_token_regex(disallowed_delimiter):
    return pypar.Regex(r"[^\s\n" + re.escape(disallowed_delimiter) + r"]+")


pypar.ParserElement.setDefaultWhitespaceChars(" \t")
table_parser = pypar.NoMatch()
table_cell_separators = ["|", "/", ","]
for separator in table_cell_separators:
    value = pypar.Combine(word_token_regex(separator) * (1, 10), joinString=' ', adjacent=False)
    row = pypar.Group(pypar.Optional(separator).suppress() +
                      (value + pypar.Literal(separator).suppress()) * (2, None) +
                      value + pypar.Optional(separator).suppress() + pypar.Literal(
        "\n").suppress() + pypar.Optional("\n").suppress())
    # Search for two or more rows of similar data
    table_parser ^= row * (2, None)

key_value_separators = [":", "-", ">"]
key_value_list_parser = pypar.NoMatch()
for separator in key_value_separators:
    value = pypar.Combine(word_token_regex(separator) * (1, 10), joinString=' ', adjacent=False)
    row = pypar.Group(value + pypar.Literal(separator).suppress() + value + pypar.Literal(
        "\n").suppress() + pypar.Optional("\n").suppress())
    key_value_list_parser ^= row * (2, None)


class StructuredDataAnnotator(Annotator):
    """
    Annotates tables and key value lists embedded in documents.
    """

    def annotate(self, doc):
        spans = []
        for token, start, end in table_parser.scanString(doc.text):
            spans.append(AnnoSpan(start, end, doc, "table", metadata={
                "type": "table",
                "data": [[value for value in row] for row in token]
            }))
        for token, start, end in key_value_list_parser.scanString(doc.text):
            spans.append(AnnoSpan(start, end, doc, "keyValuePairs", metadata={
                "type": "keyValuePairs",
                "data": {
                    pair[0]: pair[1]
                    for pair in token
                }
            }))
        return {'structuredData': AnnoTier(spans)}
