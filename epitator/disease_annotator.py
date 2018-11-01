#!/usr/bin/env python
from __future__ import absolute_import
from .annotator import Annotator, AnnoSpan, AnnoTier
from .resolved_keyword_annotator import ResolvedKeywordAnnotator
from .geoname_annotator import GeonameAnnotator


class DiseaseAnnotator(Annotator):
    def annotate(self, doc):
        geonames = doc.require_tiers('geonames', via=GeonameAnnotator)
        resolved_keywords = doc.require_tiers('resolved_keywords', via=ResolvedKeywordAnnotator)
        disease_list = []
        for kw_span in resolved_keywords:
            first_resolution = kw_span.metadata['resolutions'][0]
            if first_resolution['entity']['type'] == 'disease':
                disease_list.append(AnnoSpan(kw_span.start, kw_span.end, kw_span.doc, metadata={
                    'disease': {
                        'id': first_resolution['entity']['id'],
                        'label': first_resolution['entity']['label'],
                    }
                }))
        return {
            'diseases': AnnoTier(
                disease_list, presorted=True).without_overlaps(geonames)
        }
