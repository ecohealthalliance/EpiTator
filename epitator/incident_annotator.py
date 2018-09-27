#!/usr/bin/env python
"""
Create incidents that group together multiple layers of annotations.
This is based on the createIncidentReportsFromEnhancements function from
EIDR-Connect, although some differences exist in the output structure,
and code related to manual curation (e.g. the accepted attribute)
is not included:
https://github.com/ecohealthalliance/eidr-connect/blob/master/imports/nlp.coffee#L93
"""
from __future__ import absolute_import
from .annotator import Annotator, AnnoTier
from .annospan import AnnoSpan, SpanGroup
from .count_annotator import CountAnnotator
from .date_annotator import DateAnnotator
from .spacy_annotator import SpacyAnnotator
from .geoname_annotator import GeonameAnnotator
from .resolved_keyword_annotator import ResolvedKeywordAnnotator
from .structured_incident_annotator import StructuredIncidentAnnotator, CANNOT_PARSE
from . import utils
import datetime


def get_territories(spans, sent_spans):
    """
    A annotation's territory is the sentence containing it,
    and all the following sentences until the next annotation.
    Annotations in the same sentence are grouped.
    """
    doc = sent_spans[0].doc
    territories = []
    for sent_span, span_group in sent_spans.group_spans_by_containing_span(spans):
        if len(span_group) == 0 or len(territories) == 0:
            territories.append(AnnoSpan(
                sent_span.start, sent_span.end, doc,
                metadata=span_group))
        else:
            territories[-1] = AnnoSpan(
                territories[-1].start, sent_span.end, doc,
                metadata=territories[-1].metadata + span_group)
    return AnnoTier(territories)


class IncidentAnnotator(Annotator):
    def annotate(self, doc, case_counts=None, publish_date=None):
        if publish_date:
            publish_date = publish_date
        else:
            publish_date = datetime.datetime.now()
        if case_counts:
            case_counts = case_counts
        else:
            case_counts = doc.require_tiers('counts', via=CountAnnotator)
        resolved_keywords = doc.require_tiers(
            'resolved_keywords', via=ResolvedKeywordAnnotator)
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
        species_tier = AnnoTier(species_list)
        disease_tier = AnnoTier(disease_list)
        geonames = doc.require_tiers('geonames', via=GeonameAnnotator)
        sent_spans = doc.require_tiers('spacy.sentences', via=SpacyAnnotator)
        structured_incidents = doc.require_tiers(
            'structured_incidents', via=StructuredIncidentAnnotator)
        date_tier = doc.require_tiers('dates', via=DateAnnotator)
        dates_out = []
        for span in date_tier:
            datetime_range = list(span.metadata['datetime_range'])
            if datetime_range[0].date() > publish_date.date():
                # Omit future dates
                continue
            if datetime_range[1].date() > publish_date.date():
                # Truncate ranges that extend into the future
                datetime_range[1] = publish_date
            dates_out.append(AnnoSpan(span.start, span.end, span.doc, metadata={
                'datetime_range': datetime_range
            }))
        date_tier = AnnoTier(dates_out, presorted=True)
        date_territories = get_territories(date_tier, sent_spans)
        geoname_territories = get_territories(geonames, sent_spans)
        disease_territories = get_territories(disease_tier, sent_spans)
        # Only include the sentence the word appears in for species territories since
        # the species is implicitly human in most of the articles we're analyzing.
        species_territories = []
        for sent_span, span_group in sent_spans.group_spans_by_containing_span(species_tier):
            species_territories.append(AnnoSpan(
                sent_span.start, sent_span.end, sent_span.doc,
                metadata=span_group))
        species_territories = AnnoTier(species_territories)
        incidents = []
        for count_span in case_counts:
            count = count_span.metadata.get('count')
            attributes = set(count_span.metadata.get('attributes', []))
            if not count:
                continue
            if not set(['case', 'death']) & attributes:
                continue
            if set(['recovery', 'annual', 'monthly', 'weekly']) & attributes:
                continue
            incident_spans = [count_span]
            geoname_territory = geoname_territories.nearest_to(count_span)
            date_territory = date_territories.nearest_to(count_span)
            disease_territory = disease_territories.nearest_to(count_span)
            species_territory = species_territories.nearest_to(count_span)
            # grouping is done to deduplicate geonames
            geonames_by_id = {}
            for span in geoname_territory.metadata:
                geoname = span.metadata['geoname'].to_dict()
                del geoname['parents']
                geonames_by_id[geoname['geonameid']] = geoname
                incident_spans.append(span)
            incident_data = {
                'value': count,
                'locations': list(geonames_by_id.values())
            }
            incident_data['date_territory'] = date_territory
            incident_data['geoname_territory'] = geoname_territory
            incident_data['disease_territory'] = disease_territory
            incident_data['species_territory'] = species_territory
            # Use the document's date as the default
            incident_data['dateRange'] = [
                publish_date,
                publish_date + datetime.timedelta(days=1)]
            if len(date_territory) > 0:
                date_span = AnnoTier(date_territory.metadata).nearest_to(count_span)
                incident_data['dateRange'] = date_span.metadata['datetime_range']
                incident_spans.append(date_span)
            # A date and location must be in the count territory to create
            # an incident.
            if len(date_territory.metadata) == 0 or len(geoname_territory.metadata) == 0:
                continue
            # Detect whether count is cumulative
            date_range_duration = incident_data['dateRange'][1] - incident_data['dateRange'][0]
            cumulative = False
            if 'incremental' in attributes:
                cumulative = False
            elif 'cumulative' in attributes:
                cumulative = True
            # Infer cumulative is case rate is greater than 300 per day
            elif (count / (date_range_duration.total_seconds() / 60 / 60 / 24)) > 300:
                cumulative = True
            if 'ongoing' in attributes:
                incident_data['type'] = 'activeCount'
            elif cumulative:
                if 'case' in attributes:
                  incident_data['type'] = 'cumulativeCaseCount'
                elif 'death' in attributes:
                  incident_data['type'] = 'cumulativeDeathCount'
            else:
                if 'case' in attributes:
                  incident_data['type'] = 'caseCount'
                elif 'death' in attributes:
                  incident_data['type'] = 'deathCount'

            disease_span = AnnoTier(disease_territory.metadata).nearest_to(count_span)
            if disease_span:
                incident_data['resolvedDisease'] = disease_span.metadata['disease']
                incident_spans.append(disease_span)
            # Suggest humans as a default
            incident_data['species'] = {
                'id': 'tsn:180092',
                'label': 'Homo sapiens'
            }
            species_span = AnnoTier(species_territory.metadata).nearest_to(count_span)
            if species_span:
                incident_data['species'] = species_span.metadata['species']
                incident_spans.append(species_span)
            incidents.append(SpanGroup(incident_spans, metadata=incident_data))
        incidents += structured_incidents
        return {'incidents': AnnoTier(incidents)}
