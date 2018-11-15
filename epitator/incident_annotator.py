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
from .species_annotator import SpeciesAnnotator
from .disease_annotator import DiseaseAnnotator
from .structured_incident_annotator import StructuredIncidentAnnotator, CANNOT_PARSE
import datetime
import re
from collections import defaultdict


def capitalize(s):
    return s[0:1].upper() + s[1:]


def camelize(s):
    return "".join(
        word if idx == 0 else capitalize(word)
        for idx, word in enumerate(s.split("_")))


def format_geoname(geoname):
    """
    Format a geoname dictionary in the style of EIDR-Connect.
    """
    result = {
        "id": geoname["geonameid"]
    }
    for key, value in geoname.items():
        if key in ["geonameid", "nameCount", "namesUsed", "score", "parents"]:
            continue
        result[camelize(key)] = value
    return result


def get_territories(spans, sent_spans):
    """
    A annotation's territory is the sentence containing it,
    and all the following sentences until the next annotation.
    Annotations in the same sentence are grouped.
    """
    doc = sent_spans[0].doc
    territories = []
    for sent_span, span_group in sent_spans.group_spans_by_containing_span(spans):
        if len(territories) == 0 or len(span_group) > 0:
            territories.append(AnnoSpan(
                sent_span.start, sent_span.end, doc,
                metadata=span_group))
        else:
            prev_territory = territories[-1]
            prev_single_sent_spans = [
                span for span in prev_territory.metadata
                if span.metadata.get('scope') == 'sentence']
            if len(prev_single_sent_spans) == 0:
                territories[-1] = AnnoSpan(
                    prev_territory.start, sent_span.end, doc,
                    metadata=prev_territory.metadata)
            else:
                last_doc_scope_spans = []
                for territory in reversed(territories):
                    last_doc_scope_spans = [
                        span for span in prev_territory.metadata
                        if span.metadata.get('scope') == 'document']
                    if len(last_doc_scope_spans) > 0:
                        break
                territories.append(AnnoSpan(
                    sent_span.start, sent_span.end, doc,
                    metadata=last_doc_scope_spans))
    return AnnoTier(territories)


class IncidentAnnotator(Annotator):
    def annotate(self, doc, case_counts=None):
        if doc.date:
            publish_date = doc.date
        else:
            publish_date = datetime.datetime.now()
        if case_counts:
            case_counts = case_counts
        else:
            case_counts = doc.require_tiers('counts', via=CountAnnotator)
        geonames = doc.require_tiers('geonames', via=GeonameAnnotator)
        sent_spans = doc.require_tiers('spacy.sentences', via=SpacyAnnotator)
        disease_tier = doc.require_tiers('diseases', via=DiseaseAnnotator)
        species_tier = doc.require_tiers('species', via=SpeciesAnnotator)
        disease_mentions = defaultdict(lambda: 0)
        for span in disease_tier:
            disease_mentions[span.metadata['disease']['id']] += 1
        # Copy disease tier
        disease_tier = AnnoTier([
            AnnoSpan(span.start, span.end, span.doc, metadata=span.metadata)
            for span in disease_tier], presorted=True)
        # scope one off disease mentions to sentences.
        max_disease = max(disease_mentions.values()) if len(disease_mentions) > 0 else 0
        if max_disease > 5:
            for span in disease_tier:
                if disease_mentions[span.metadata['disease']['id']] == 1:
                    span.metadata['scope'] = 'sentence'
                else:
                    span.metadata['scope'] = 'document'

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
                datetime_range[1] = datetime.datetime(publish_date.year, publish_date.month, publish_date.day)
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
                geonames_by_id[geoname['geonameid']] = format_geoname(geoname)
                incident_spans.append(span)
            incident_data = {
                'value': count,
                'locations': list(geonames_by_id.values())
            }
            incident_data['count_annotation'] = count_span
            incident_data['date_territory'] = date_territory
            incident_data['geoname_territory'] = geoname_territory
            incident_data['disease_territory'] = disease_territory
            incident_data['species_territory'] = species_territory
            # Use the document's date as the default
            incident_data['dateRange'] = [
                publish_date,
                publish_date + datetime.timedelta(days=1)]
            cumulative = False
            if len(date_territory.metadata) > 0:
                date_span = AnnoTier(date_territory.metadata).nearest_to(count_span)
                as_of_dates = doc.create_regex_tier(
                    re.compile(r"\bas of\b", re.I)
                ).with_following_spans_from([date_span], max_dist=8, allow_overlap=True)
                cumulative = len(as_of_dates) > 0
                incident_data['dateRange'] = date_span.metadata['datetime_range']
                incident_spans.append(date_span)
            # A date and location must be in the count territory to create
            # an incident.
            if len(date_territory.metadata) == 0 or len(geoname_territory.metadata) == 0:
                continue
            # Detect whether count is cumulative
            date_range_duration = incident_data['dateRange'][1] - incident_data['dateRange'][0]
            duration_days = date_range_duration.total_seconds() / 60 / 60 / 24
            incident_data['duration'] = duration_days
            if cumulative:
                pass
            elif 'incremental' in attributes:
                cumulative = False
            elif 'cumulative' in attributes:
                cumulative = True
            elif date_range_duration.total_seconds() == 0:
                cumulative = True
            # Infer cumulative is case rate is greater than 300 per day
            elif count / duration_days > 300:
                cumulative = True

            if 'ongoing' in attributes:
                incident_data['type'] = 'activeCount'
            elif cumulative:
                if 'case' in attributes:
                    incident_data['type'] = 'cumulativeCaseCount'
                if 'death' in attributes:
                    incident_data['type'] = 'cumulativeDeathCount'
            else:
                if 'case' in attributes:
                    incident_data['type'] = 'caseCount'
                if 'death' in attributes:
                    incident_data['type'] = 'deathCount'

            disease_span = AnnoTier(disease_territory.metadata).nearest_to(count_span)
            if disease_span:
                incident_data['resolvedDisease'] = dict(disease_span.metadata['disease'])
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
            incident_data['approximate'] = 'approximate' in attributes
            if 'suspected' in attributes:
                incident_data['status'] = 'suspected'
            elif 'confirmed' in attributes:
                incident_data['status'] = 'confirmed'
            incidents.append(SpanGroup(incident_spans, metadata=incident_data))
        for incident in structured_incidents:
            if not incident.metadata.get('dateRange') or not incident.metadata.get('location'):
                continue
            required_properties = [
                incident.metadata['type'],
                incident.metadata['dateRange'],
                incident.metadata['location'],
                incident.metadata['value']]
            if CANNOT_PARSE in required_properties:
                continue
            metadata = dict(incident.metadata)
            if metadata['species'] == CANNOT_PARSE:
                metadata['species'] = {
                    'id': 'tsn:180092',
                    'label': 'Homo sapiens'
                }
            if metadata['resolvedDisease'] == CANNOT_PARSE:
                del metadata['resolvedDisease']
            if "suspected" in metadata['attributes']:
                metadata['status'] = "suspected"
            elif "confirmed" in metadata['attributes']:
                metadata['status'] = "confirmed"
            metadata['locations'] = [format_geoname(metadata['location'])]
            del metadata['location']
            incidents.append(SpanGroup([incident], metadata=metadata))
        return {'incidents': AnnoTier(incidents)}
