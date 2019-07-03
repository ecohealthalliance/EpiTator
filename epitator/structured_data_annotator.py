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
    value = pypar.Combine(
        word_token_regex(separator) * (0, 10),
        joinString=' ',
        adjacent=False)
    value.setParseAction(lambda start, tokens: (start, tokens[0]))
    empty = pypar.Empty()
    empty.setParseAction(lambda start, tokens: (start, tokens))
    value = pypar.Group(value + empty)
    row = pypar.Group(pypar.Optional(separator).suppress() +
                      (value + pypar.Literal(separator).suppress()) * (1, None) +
                      pypar.Optional(value) +
                      (pypar.StringEnd() | pypar.Literal("\n")).suppress() +
                      pypar.Optional("\n").suppress())
    table_parser ^= (
        (pypar.LineStart() + pypar.Optional(pypar.White())).suppress() +
        # Allow line breaks for table headings
        row + pypar.Optional(pypar.Regex(r"[\-_=]{3,}") + pypar.Literal("\n") * (1, 2)).suppress() +
        row * (0, None)).setResultsName("delimiter:" + separator)
table_parser.parseWithTabs()

key_value_separators = [":", "-", ">"]
key_value_list_parser = pypar.NoMatch()
for separator in key_value_separators:
    value = pypar.Combine(
        word_token_regex(separator) * (1, 10),
        joinString=' ',
        adjacent=False)
    value.setParseAction(lambda start, tokens: (start, tokens[0]))
    empty = pypar.Empty()
    empty.setParseAction(lambda start, tokens: (start, tokens))
    value = pypar.Group(value + empty)
    row = pypar.Group(value + pypar.Literal(separator).suppress() + value +
                      (pypar.StringEnd() | pypar.Literal("\n")).suppress() +
                      pypar.Optional("\n").suppress())
    key_value_list_parser ^= (
        (pypar.LineStart() + pypar.Optional(pypar.White())).suppress() +
        row * (2, None)).setResultsName("delimiter:" + separator)
key_value_list_parser.parseWithTabs()


class StructuredDataAnnotator(Annotator):
    """
    Annotates tables and key value lists embedded in documents.
    """

    def annotate(self, doc):
        doc_text_len = len(doc.text)

        def create_trimmed_annospan_for_doc(start, end, label=None, metadata=None):
            return AnnoSpan(
                start,
                min(doc_text_len, end),
                doc,
                label=label,
                metadata=metadata).trimmed()

        spans = []
        value_spans = []
        for token, start, end in table_parser.scanString(doc.text):
            data = [[
                create_trimmed_annospan_for_doc(value_start, value_end)
                for ((value_start, value), (value_end, _)) in row] for row in token]
            new_value_spans = [value for row in data for value in row]
            # Skip tables with one row and numeric/empty columns since they are likely
            # to be confused with unstructured text punctuation.
            if len(data) == 1:
                if len(new_value_spans) < 3:
                    continue
                elif any(re.match(r"\d*$", value.text) for value in new_value_spans):
                    continue
            # Skip tables with differing numbers of columns in each row
            else:
                row_lengths = sorted([len(row) for row in data])
                # Determine the min and max difference between any two row lengths.
                max_diff = row_lengths[-1] - row_lengths[0]
                min_diff = max_diff
                for row_len, next_row_len in zip(row_lengths, row_lengths[1:]):
                    len_diff = next_row_len - row_len
                    if len_diff < min_diff:
                        min_diff = len_diff
                if min_diff > 0 and max_diff > 1:
                    continue
            spans.append(create_trimmed_annospan_for_doc(start, end, "table", metadata={
                "type": "table",
                "data": data,
                "delimiter": next(k.split("delimiter:")[1] for k in token.keys() if k.startswith("delimiter:"))
            }))
            value_spans += new_value_spans
        for token, start, end in key_value_list_parser.scanString(doc.text):
            data = {
                create_trimmed_annospan_for_doc(key_start, key_end): create_trimmed_annospan_for_doc(value_start, value_end)
                for (((key_start, key), (key_end, _)), ((value_start, value), (value_end, _2))) in token
            }
            spans.append(create_trimmed_annospan_for_doc(start, end, "keyValuePairs", metadata={
                "type": "keyValuePairs",
                "data": data,
                "delimiter": next(k.split("delimiter:")[1] for k in token.keys() if k.startswith("delimiter:"))
            }))
            value_spans += data.values()
        return {
            'structured_data': AnnoTier(spans),
            'structured_data.values': AnnoTier(value_spans)
        }
