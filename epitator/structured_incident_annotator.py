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
import re
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


CANNOT_PARSE = "Cannot parse"


class Table():
    def __init__(self, column_definitions, rows, metadata=None):
        self.column_definitions = column_definitions
        self.rows = rows
        self.metadata = metadata or {}


def is_null(val_string):
    val_string = val_string.strip()
    return val_string == "" or val_string == "-"


def median(li):
    if len(li) == 0:
        return None
    mid_idx = int((len(li) - 1) / 2)
    li = sorted(li)
    if len(li) % 2 == 1:
        return li[mid_idx]
    else:
        return (li[mid_idx] + li[mid_idx + 1]) / 2


def merge_metadata(sofar, child_metadata):
    # prefer highest weighted species
    if "species" in sofar and "species" in child_metadata:
        if sofar['species']['weight'] < child_metadata['species']['weight']:
            return dict(child_metadata, **dict(sofar, species=child_metadata['species']))
    return dict(child_metadata, **sofar)


def combine_metadata(spans):
    """
    Return the merged metadata dictionaries from all descendant spans.
    Presedence of matching properties follows the order of a pre-order tree traversal.
    """
    result = {}
    for span in spans:
        child_metadata = combine_metadata(span.base_spans)
        if span.metadata:
            child_metadata = merge_metadata(span.metadata, child_metadata)
        result = merge_metadata(result, child_metadata)
    return result


def split_list(li):
    group = []
    for value in li:
        if value:
            group.append(value)
        else:
            if len(group) > 0:
                yield group
                group = []
    if len(group) > 0:
        yield group


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
        species_list = []
        disease_list = []
        for k in resolved_keywords:
            for resolution in k.metadata.get('resolutions', []):
                if resolution['entity']['type'] == 'species':
                    species_list.append(AnnoSpan(
                        k.start,
                        k.end,
                        k.doc,
                        metadata={'species': resolution}))
                    break
            for resolution in k.metadata.get('resolutions', []):
                if resolution['entity']['type'] == 'disease':
                    disease_list.append(AnnoSpan(
                        k.start,
                        k.end,
                        k.doc,
                        metadata={'disease': resolution}))
                    break
        entities_by_type = {
            'geoname': geonames,
            'date': dates,
            'species': AnnoTier(species_list).optimal_span_set(),
            'disease': AnnoTier(disease_list, presorted=True),
            'integer': AnnoTier([
                span
                for span in numbers
                if span.metadata['number'] == int(span.metadata['number'])
            ], presorted=True),
            'incident_type': spacy_tokens.search_spans(r'(case|death)s?'),
            'incident_status': spacy_tokens.search_spans(r'suspected|confirmed'),
        }
        tables = []
        possible_titles = doc.create_regex_tier("[^\n]+\n")\
            .chains(at_most=4, max_dist=0)\
            .without_overlaps(doc.tiers['structured_data'])\
            .optimal_span_set(prefer='text_length_min_spans')
        for span in doc.tiers['structured_data'].spans:
            if span.metadata['type'] != 'table':
                continue
            # Add virtual metadata columns based on surrounding text from
            # title sentence/paragraph.
            table_title = possible_titles.span_before(span)
            if table_title:
                table_title = AnnoSpan(
                    table_title.start,
                    min(table_title.end, span.start),
                    doc)
            last_disease_mentioned = entities_by_type['disease'].span_before(span)
            last_geoname_mentioned = None
            last_date_mentioned = None
            last_species_mentioned = None
            if table_title:
                last_species_mentioned = next(iter(AnnoTier(
                    species_list,
                    presorted=True
                ).spans_contained_by_span(table_title).spans[-1:]), None)
                last_geoname_mentioned = next(iter(AnnoTier(
                    geonames,
                    presorted=True
                ).spans_contained_by_span(table_title).spans[-1:]), None)
                last_date_mentioned = next(iter(AnnoTier(
                    dates,
                    presorted=True
                ).spans_contained_by_span(table_title).spans[-1:]), None)
            rows = span.metadata['data']
            # Detect header
            first_row = AnnoTier(rows[0])
            header_entities = list(first_row.group_spans_by_containing_span(numbers))
            header_numeric_portions = [
                sum(len(s) for s in entity_spans) * 1.0 / len(header_span)
                for header_span, entity_spans in header_entities
                if len(header_span) > 0]
            if all(portion < 0.8 for portion in header_numeric_portions):
                has_header = True
            else:
                has_header = False
            if has_header:
                data_rows = rows[1:]
            else:
                data_rows = rows

            # Remove rows without the right number of columns
            median_num_cols = median(list(map(len, data_rows)))
            data_rows = [row for row in data_rows if len(row) == median_num_cols]

            # Determine column types
            table_by_column = list(zip(*data_rows))
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
                    if value_type == "integer":
                        filtered_value_spans = value_spans.without_overlaps(dates)
                    column_entities = [
                        SpanGroup(contained_spans, metadata=combine_metadata(contained_spans)) if len(contained_spans) > 0 else None
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
                for column_type, header_name in zip(column_types + len(first_row) * [None], first_row):
                    column_definitions.append({
                        'name': header_name,
                        'type': column_type
                    })
            else:
                column_definitions = [
                    {'type': column_type}
                    for column_type in column_types]
            date_period = None
            for column_def, entities in zip(column_definitions, parsed_column_entities):
                if column_def['type'] == 'date':
                    date_diffs = []
                    for entity_group in split_list(entities):
                        date_diffs += [
                            abs(d.metadata['datetime_range'][0] - next_d.metadata['datetime_range'][0])
                            for d, next_d in zip(entity_group, entity_group[1:])]
                    date_period = median(date_diffs)
                    break
            # Implicit metadata has to come first so values in other rows will
            # overrite it.
            parsed_column_entities = [
                len(data_rows) * [last_geoname_mentioned],
                len(data_rows) * [last_date_mentioned],
                len(data_rows) * [last_disease_mentioned],
                len(data_rows) * [last_species_mentioned],
            ] + parsed_column_entities
            column_definitions = [
                {'name': '__implicit_metadata', 'type': 'geoname'},
                {'name': '__implicit_metadata', 'type': 'date'},
                {'name': '__implicit_metadata', 'type': 'disease'},
                {'name': '__implicit_metadata', 'type': 'species'}
            ] + column_definitions
            rows = list(zip(*parsed_column_entities))
            # merge with prior table or create a new one
            if not has_header and len(tables) > 0 and len(column_definitions) == len(tables[-1].column_definitions):
                # Special case for merging detached header rows
                if len(tables[-1].rows) == 0:
                    tables[-1].rows = rows
                    tables[-1].column_definitions = [
                        {
                            'type': definition.get('type'),
                            'name': definition.get('name') or prev_definition.get('name')}
                        for definition, prev_definition in zip(column_definitions, tables[-1].column_definitions)]
                elif [d['type'] for d in column_definitions] == [d['type'] for d in tables[-1].column_definitions]:
                    tables[-1].rows += rows
                    tables[-1].column_definitions = [
                        {
                            'type': definition.get('type') or prev_definition.get('type'),
                            'name': definition.get('name') or prev_definition.get('name')}
                        for definition, prev_definition in zip(column_definitions, tables[-1].column_definitions)]
            else:
                tables.append(Table(
                    column_definitions,
                    rows,
                    metadata=dict(
                        title=table_title,
                        date_period=date_period,
                        aggregation="cumulative" if table_title and re.search("cumulative", table_title.text, re.I) else None,
                        # The default metadata will be used as a final fallback
                        # for multi-section tables. When values are not specified
                        # in section titles, the values from the table title
                        # are used.
                        default_geoname=last_geoname_mentioned,
                        default_disease=last_disease_mentioned,
                        default_species=last_species_mentioned,
                        default_date=last_date_mentioned
                    )))
        incidents = []
        for table in tables:
            logger.info("header:")
            logger.info(table.column_definitions)
            logger.info("%s rows" % len(table.rows))
            for row_idx, row in enumerate(table.rows):
                row_incident_date = table.metadata.get('default_date')
                row_incident_location = table.metadata.get('default_geoname')
                row_incident_species = table.metadata.get('default_species')
                row_incident_disease = table.metadata.get('default_disease')
                row_incident_base_type = None
                row_incident_status = None
                row_incident_aggregation = table.metadata.get('aggregation')
                for column, value in zip(table.column_definitions, row):
                    if column.get('name') == "__implicit_metadata" and not value:
                        continue
                    if not value:
                        value = CANNOT_PARSE
                    if column['type'] == 'date':
                        row_incident_date = value
                    elif column['type'] == 'geoname':
                        row_incident_location = value
                    elif column['type'] == 'species':
                        row_incident_species = value
                    elif column['type'] == 'incident_type':
                        if value == CANNOT_PARSE:
                            row_incident_base_type = value
                        elif "case" in value.text.lower():
                            row_incident_base_type = "caseCount"
                        elif "death" in value.text.lower():
                            row_incident_base_type = "deathCount"
                        else:
                            row_incident_base_type = CANNOT_PARSE
                    elif column['type'] == 'incident_status':
                        row_incident_status = value

                row_incidents = []
                for column, value in zip(table.column_definitions, row):
                    if not value:
                        continue
                    if column['type'] == "integer":
                        column_name = column.get('name')
                        if isinstance(column_name, AnnoSpan):
                            column_name_text = column_name.text.lower()
                        else:
                            column_name_text = (column_name or '').lower()
                        incident_base_type = None
                        if row_incident_base_type:
                            incident_base_type = row_incident_base_type
                        elif "cases" in column_name_text:
                            incident_base_type = "caseCount"
                        elif "deaths" in column_name_text:
                            incident_base_type = "deathCount"

                        if row_incident_status and row_incident_status != CANNOT_PARSE:
                            count_status = row_incident_status.text
                        elif "suspect" in column_name_text or column_name_text == "reported":
                            count_status = "suspected"
                        elif "confirmed" in column_name_text:
                            count_status = "confirmed"
                        else:
                            count_status = None

                        if count_status and not incident_base_type:
                            incident_base_type = "caseCount"
                        incident_aggregation = None
                        if row_incident_aggregation is not None:
                            incident_aggregation = row_incident_aggregation
                        if "total" in column_name_text:
                            incident_aggregation = "cumulative"
                        if "new" in column_name_text:
                            incident_aggregation = "incremental"
                        incident_count = value.metadata['number']
                        incident_location = row_incident_location
                        incident_species = row_incident_species
                        incident_disease = row_incident_disease
                        incident_date = row_incident_date
                        if incident_species and incident_species != CANNOT_PARSE:
                            species_entity = incident_species.metadata['species']['entity']
                            incident_species = {
                                'id': species_entity['id'],
                                'label': species_entity['label'],
                            }
                        elif not incident_base_type and isinstance(column_name, AnnoSpan):
                            contained_spans = entities_by_type['species'].spans_contained_by_span(column_name)
                            if len(contained_spans) > 0:
                                incident_base_type = "caseCount"
                                entity = contained_spans[0].metadata['species']['entity']
                                incident_species = {
                                    'id': entity['id'],
                                    'label': entity['label'],
                                }

                        if incident_disease and incident_disease != CANNOT_PARSE:
                            disease_entity = incident_disease.metadata['disease']['entity']
                            incident_disease = {
                                'id': disease_entity['id'],
                                'label': disease_entity['label'],
                            }
                        elif not incident_base_type and isinstance(column_name, AnnoSpan):
                            contained_spans = entities_by_type['disease'].spans_contained_by_span(column_name)
                            if len(contained_spans) > 0:
                                incident_base_type = "caseCount"
                                entity = contained_spans[0].metadata['disease']['entity']
                                incident_disease = {
                                    'id': entity['id'],
                                    'label': entity['label'],
                                }

                        if incident_location and incident_location != CANNOT_PARSE:
                            incident_location = incident_location.metadata['geoname'].to_dict()
                            del incident_location['parents']
                        elif not incident_base_type and isinstance(column_name, AnnoSpan):
                            contained_spans = entities_by_type['geoname'].spans_contained_by_span(column_name)
                            if len(contained_spans) > 0:
                                incident_base_type = "caseCount"
                                incident_location = contained_spans[0].metadata['geoname'].to_dict()
                                del incident_location['parents']

                        if incident_date != CANNOT_PARSE:
                            if incident_date:
                                incident_date = incident_date.metadata['datetime_range']
                            if table.metadata.get('date_period'):
                                if incident_aggregation != "cumulative":
                                    incident_date = [
                                        incident_date[1] - table.metadata.get('date_period'),
                                        incident_date[1]]
                        if not incident_base_type:
                            continue
                        row_incidents.append(AnnoSpan(value.start, value.end, doc, metadata={
                            'base_type': incident_base_type,
                            'aggregation': incident_aggregation,
                            'value': incident_count,
                            'attributes': list(filter(lambda x: x, [count_status])),
                            'location': incident_location,
                            'resolvedDisease': incident_disease,
                            'dateRange': incident_date,
                            'species': incident_species
                        }))
                # If a count is marked as incremental if a count in the row greater
                # than it is cumulative.
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
                    if incident['aggregation'] is None:
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
