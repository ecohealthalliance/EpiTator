#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier
from .annospan import AnnoSpan, SpanGroup
from .structured_data_annotator import StructuredDataAnnotator
from .geoname_annotator import GeonameAnnotator
from .resolved_keyword_annotator import ResolvedKeywordAnnotator
from .spacy_annotator import SpacyAnnotator
from .date_annotator import DateAnnotator
from .raw_number_annotator import RawNumberAnnotator
from . import utils


class Table():
    def __init__(self, column_definitions, rows, metadata=None):
        self.column_definitions = column_definitions
        self.rows = rows
        self.metadata = metadata or {}


def is_null(val_string):
    val_string = val_string.strip()
    return val_string == "" or val_string == "-"


def median(li):
    mid_idx = (len(li) - 1) / 2
    li = sorted(li)
    if len(li) % 2 == 1:
        return li[mid_idx]
    else:
        return (li[mid_idx] + li[mid_idx + 1]) / 2


class StructuredIncidentAnnotator(Annotator):
    """
    The structured incident annotator will find groupings of case counts and incidents
    """

    def annotate(self, doc):
        if 'structured_data' not in doc.tiers:
            doc.add_tiers(StructuredDataAnnotator())
        if 'geonames' not in doc.tiers:
            doc.add_tiers(GeonameAnnotator())
        if 'dates' not in doc.tiers:
            doc.add_tiers(DateAnnotator())
        if 'resolved_keywords' not in doc.tiers:
            doc.add_tiers(ResolvedKeywordAnnotator())
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        if 'raw_numbers' not in doc.tiers:
            doc.add_tiers(RawNumberAnnotator())

        geonames = doc.tiers['geonames']
        dates = doc.tiers['dates']
        resolved_keywords = doc.tiers['resolved_keywords']
        spacy_tokens = doc.tiers['spacy.tokens']
        numbers = doc.tiers['raw_numbers']

        entities_by_type = {
            'geoname': geonames,
            'date': dates,
            'resolved_keyword': resolved_keywords,
            'number': numbers,
            'incident_type': spacy_tokens.search_spans(r'(case|death)s?'),
            'incident_status': spacy_tokens.search_spans(r'suspected|confirmed'),
        }

        tables = []
        for span in doc.tiers['structured_data'].spans:
            if span.metadata['type'] != 'table': continue
            # Add columns based on surrounding text
            __section_title = doc.tiers['spacy.sentences'].nearest_prior_span(span)
            __last_geoname_mentioned = geonames.nearest_prior_span(span)
            __last_date_mentioned = dates.nearest_prior_span(span)
            rows = span.metadata['data']
            # Detect header
            all_entities = [value
                for value_group in entities_by_type.values()
                for value in value_group]
            first_row = AnnoTier(rows[0])
            header_entities = list(first_row.group_spans_by_containing_span(numbers))
            if all(len(entity_spans) == 0 for header_span, entity_spans in header_entities):
                has_header = True
            else:
                has_header = False
            if has_header:
                data_rows = rows[1:]
            else:
                data_rows = rows

            # Determine column types
            table_by_column = zip(*data_rows)
            column_types = []
            parsed_column_entities = []
            for column_values in table_by_column:
                num_non_null_rows = sum(not is_null(value.text) for value in column_values)
                column_values = AnnoTier(column_values)
                # Choose column type based on greatest percent match,
                # if under 30, choose text.
                max_matches = 0
                matching_column_entities = None
                column_type = "text"
                for value_type, value_spans in entities_by_type.items():
                    filtered_value_spans = value_spans
                    if value_type == "number":
                        filtered_value_spans = value_spans.without_overlaps(dates)
                    column_entities = [
                        SpanGroup(contained_spans) if len(contained_spans) > 0 else None
                        for group_span, contained_spans in column_values.group_spans_by_containing_span(filtered_value_spans)]
                    num_matches = sum(
                        contained_spans is not None
                        for contained_spans in column_entities)
                    
                    if num_non_null_rows > 0 and float(num_matches) / num_non_null_rows > 0.3:
                        if num_matches > max_matches:
                            max_matches = num_matches
                            matching_column_entities = column_entities
                            column_type = value_type
                    if matching_column_entities is None:
                        matching_column_entities = [[] for x in column_values]
                column_types.append(column_type)
                parsed_column_entities.append(matching_column_entities)
            column_definitions = []
            if has_header:
                for column_type, header_name in zip(column_types, first_row):
                    column_definitions.append({
                        'name': header_name.text,
                        'type': column_type
                    })
            else:
                column_definitions = [
                    {'type': column_type}
                    for column_type in column_types]
            # Adjust columns
            # median_num_cols = median(map(len, rows))
            # for row in rows:
            #     if len(row) > median_num_cols:
            #         combine cols with unexpected types
            #     elif len(row) < median_num_cols:
            #         add empty cols or remove row
            #     else:
            #         good

            # prior_table = None
            # if len(tables) > 0:
            #     prior_table = tables[-1]
            # //combine with previous table
            # if not has_header and prior_table and len(prior_table.header) == median_num_cols:
            #     # TODO: Check matching column types

            rows = zip(*parsed_column_entities)
            tables.append(Table(
                column_definitions,
                rows,
                metadata=dict(
                    __section_title=__section_title,
                    __last_geoname_mentioned=__last_geoname_mentioned,
                    __last_date_mentioned=__last_date_mentioned)))

        incidents = []
        for table in tables:
            for row_idx, row in enumerate(table.rows):
                row_incident_date = table.metadata.get('__last_date_mentioned')
                row_incident_location = table.metadata.get('__last_geoname_mentioned')
                row_incident_base_type = None
                row_incident_status = None
                row_incident_aggregation = None
                for column, value in zip(table.column_definitions, row):
                    if not value: continue
                    if column['type'] == 'date':
                        row_incident_date = value
                    elif column['type'] == 'geoname':
                        row_incident_location = value
                    elif column['type'] == 'incident_type':
                        if "case" in value.text.lower():
                            row_incident_base_type = "caseCount"
                        elif "death" in value.text.lower():
                            row_incident_base_type = "deathCount"
                    elif column['type'] == 'incident_status':
                        row_incident_status = value.text

                row_incidents = []
                for column, value in zip(table.column_definitions, row):
                    if not value: continue
                    if column['type'] == "number":
                        column_name = column.get('name', '').lower()
                        if row_incident_base_type:
                            incident_base_type = row_incident_base_type
                        else:
                            if "cases" in column_name:
                                incident_base_type = "caseCount"
                            elif "deaths" in column_name:
                                incident_base_type = "deathCount"
                            else:
                                incident_base_type = "caseCount"
                        if row_incident_status:
                            count_status = row_incident_status
                        else:
                            if "suspect" in column_name:
                                count_status = "suspected"
                            elif "confirmed" in column_name:
                                count_status = "confirmed"
                            else:
                                count_status = None
                        incident_aggregation = None
                        if row_incident_aggregation is not None:
                            incident_aggregation = row_incident_aggregation
                        elif "total" in column_name:
                            incident_aggregation = "cumulative"
                        elif "new" in column_name:
                            incident_aggregation = "incremental"
                        incident_count = utils.parse_spelled_number(value.text)
                        incident_location = row_incident_location
                        incident_date = row_incident_date
                        row_incidents.append(AnnoSpan(value.start, value.end, doc, metadata={
                            'base_type': incident_base_type,
                            'aggregation': incident_aggregation,
                            'value': incident_count,
                            'attributes': filter(lambda x: x, [count_status]),
                            'location': incident_location.combined_metadata()['geoname'].to_dict() if incident_location else None,
                            'dateRange': incident_date.combined_metadata()['datetime_range'] if incident_date else None
                        }))
                # If a count is marked as incremental any count in the row above
                # that value is considered cumulative.
                max_new_cases = -1
                max_new_deaths = -1
                for incident_span in row_incidents:
                    incident = incident_span.metadata
                    if incident['aggregation'] == "incremental":
                        if incident['base_type'] == 'caseCount':
                            if max_new_cases < incident['value']:
                                max_new_cases = incident['value']
                        else:
                            if max_new_deaths < incident['value']:
                                max_new_deaths = incident['value']
                for incident_span in row_incidents:
                    incident = incident_span.metadata
                    if incident['aggregation'] == None:
                        if incident['base_type'] == 'caseCount':
                            if max_new_cases >= 0 and incident['value'] > max_new_cases:
                                incident['aggregation'] = 'cumulative'
                        else:
                            if max_new_deaths >= 0 and incident['value'] > max_new_deaths:
                                incident['aggregation'] = 'cumulative'
                for incident_span in row_incidents:
                    incident = incident_span.metadata
                    if incident['aggregation'] == 'cumulative':
                        incident['type'] = "cumulative" + incident['base_type'][0].upper() + incident['base_type'][1:]
                    else:
                        incident['type'] = incident['base_type']
                    del incident['base_type']
                    del incident['aggregation']
                incidents.extend(row_incidents)
        return {'structured_incidents': AnnoTier(incidents)}
