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
    value = pypar.Combine(word_token_regex(separator) * (0, 10), joinString=' ', adjacent=False)
    value.setParseAction(lambda start, tokens: (start, tokens[0]))
    empty = pypar.Empty()
    empty.setParseAction(lambda start, tokens: (start, tokens))
    value = pypar.Group(value + empty)
    row = pypar.Group(pypar.Optional(separator).suppress() +
                      (value + pypar.Literal(separator).suppress()) * (1, None) +
                      pypar.Optional(value) +
                      pypar.Literal("\n").suppress() +
                      pypar.Optional("\n").suppress())
    table_parser ^= row * (1, None)

key_value_separators = [":", "-", ">"]
key_value_list_parser = pypar.NoMatch()
for separator in key_value_separators:
    value = pypar.Combine(word_token_regex(separator) * (1, 10), joinString=' ', adjacent=False)
    value.setParseAction(lambda start, tokens: (start, tokens[0]))
    empty = pypar.Empty()
    empty.setParseAction(lambda start, tokens: (start, tokens))
    value = pypar.Group(value + empty)
    row = pypar.Group(value + pypar.Literal(separator).suppress() + value + pypar.Literal(
        "\n").suppress() + pypar.Optional("\n").suppress())
    key_value_list_parser ^= row * (2, None)


class StructuredDataAnnotator(Annotator):
    """
    Annotates tables and key value lists embedded in documents.
    """

    def annotate(self, doc):
        spans = []
        value_spans = []
        for token, start, end in table_parser.scanString(doc.text):
            data = [[
                AnnoSpan(value_start, value_end, doc).trimmed()
                for ((value_start, value), (value_end, _)) in row] for row in token]
            new_value_spans = [value for row in data for value in row]
            # Skip tables with one row and numeric/empty columns since they are likely
            # to be confused with unstructured text punctuation.
            if len(data) == 1:
                if len(new_value_spans) < 3:
                    continue
                elif any(re.match(r"\d*$", value.text) for value in new_value_spans):
                    continue
            spans.append(AnnoSpan(start, end, doc, "table", metadata={
                "type": "table",
                "data": data
            }))
            value_spans += new_value_spans
        for token, start, end in key_value_list_parser.scanString(doc.text):
            data = {
                AnnoSpan(key_start, key_end, doc).trimmed(): AnnoSpan(value_start, value_end, doc).trimmed()
                for (((key_start, key), (key_end, _)), ((value_start, value), (value_end, _2))) in token
            }
            spans.append(AnnoSpan(start, end, doc, "keyValuePairs", metadata={
                "type": "keyValuePairs",
                "data": data
            }))
            value_spans += data.values()
        return {
            'structured_data': AnnoTier(spans),
            'structured_data.values': AnnoTier(value_spans)
        }
