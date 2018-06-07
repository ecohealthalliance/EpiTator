#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
from .resolved_keyword_annotator import ResolvedKeywordAnnotator
from .geoname_annotator import GeonameAnnotator
from .spacy_annotator import SpacyAnnotator


class SpeciesAnnotator(Annotator):
    def annotate(self, doc):
        named_entities = doc.require_tiers('spacy.nes', via=SpacyAnnotator)
        geonames = doc.require_tiers('geonames', via=GeonameAnnotator)
        resolved_keywords = doc.require_tiers('resolved_keywords', via=ResolvedKeywordAnnotator)
        species_list = []
        for kw_span in resolved_keywords:
            first_resolution = kw_span.metadata['resolutions'][0]
            if first_resolution['entity']['type'] == 'species':
                species_list.append(AnnoSpan(kw_span.start, kw_span.end, kw_span.doc, metadata={
                    'species': {
                        'id': first_resolution['entity']['id'],
                        'label': first_resolution['entity']['label'],
                    }
                }))
        species_tier = AnnoTier(species_list, presorted=True)
        return {
            'species': species_tier.without_overlaps(geonames).without_overlaps(named_entities)
        }
