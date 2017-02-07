#!/usr/bin/env python
"""Geoname Annotator"""
import math
import re
import itertools
import sqlite3
import os

from annotator import *
from ngram_annotator import NgramAnnotator
from ne_annotator import NEAnnotator
from geopy.distance import great_circle
from maximum_weight_interval_set import Interval, find_maximum_weight_interval_set

from get_database_connection import get_database_connection
import math
from geoname_classifier import predict_proba

import datetime
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

# TODO: We might be able to remove some of these names in a more general way
# by adding a feature to the scoring function.
blocklist = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'August', 'September', 'October', 'November', 'December',
    'North', 'East', 'West', 'South',
    'Northeast', 'Southeast', 'Northwest', 'Southwest',
    'Eastern', 'Western', 'Southern', 'Northern',
    'About', 'Many', 'See', 'As', 'About', 'Health',
    'International', 'City', 'World', 'Federal', 'Federal District',
    'British', 'Russian',
    'Valley', 'University', 'Center', 'Central',
    # These locations could be legitimate,
    # but they are rarely referred to in a context
    # where its location is relevent.
    'National Institutes of Health',
    'Centers for Disease Control',
    'Ministry of Health and Sanitation',
]

def location_contains(loc_outer, loc_inner):
    """
    Do a comparison to see if one geonames location contains another.
    It returns an integer to indicate how specific the containment is.
    USA contains Texas should be a smaller integer than WA contains Seattle.
    0 indicates no containment. Siblings locations and identical locations
    have 0 containment.
    This is not guarenteed to be correct, it is based on my assumptions
    about the geonames heirarchy.
    """
    # This doesn't work for every feature class
    # ADM... or PPL... features are most likely to work.
    # I'm not sure how to deal with RGN and CONT, the geonames website has
    # a parent heirarchy in the UI but I'm not sure where the data comes from.
    props = [
        'country_code',
        'admin1_code',
        'admin2_code',
        'admin3_code',
        'admin4_code'
    ]
    for idx, prop in enumerate(props):
        if len(loc_outer[prop]) == 0:
            if len(loc_inner[prop]) == 0:
                return 0 # locations appear to be siblings/identical
            else:
                return idx
        if loc_outer[prop] != loc_inner[prop]:
            return 0
    return 0 # locations appear to be siblings/identical

class GeoSpan(AnnoSpan):
    def __init__(self, start, end, doc, geoname):
        self.start = start
        self.end = end
        self.doc = doc
        self.geoname = geoname
        self.label = geoname['name']
    def to_dict(self):
        result = super(GeoSpan, self).to_dict()
        result['geoname'] = self.geoname.to_dict()
        return result

class GeonameRow(sqlite3.Row):
    def __init__(self, *args):
        super(GeonameRow, self).__init__(*args)
        self.alternate_locations = set()
        self.spans = set()
        self.parent_location = None
        self.score = None
    def add_spans(self, span_text_to_spans):
        for name in self['names_used'].split(';'):
            for span in span_text_to_spans[name.lower().strip()]:
                self.spans.add(span)
    def __hash__(self):
        return id(self)
    def __repr__(self):
        return self['name']
    def to_dict(self):
        result = {}
        for key in self.keys():
            result[key] = self[key]
        if self.parent_location:
            result['parent_location'] = self.parent_location.to_dict()
        result['score'] = self.score
        return result

def feature(fun):
    """
    A decorator for designatic which methods are used to create features.
    """
    fun.is_feature = True
    return fun

class GeonameFeatures(object):
    def __init__(self, geoname):
        self.geoname = geoname
        self.feature_dict = {
            feature_name: feature_fun(self)
            for feature_name, feature_fun in GeonameFeatures.__dict__.items()
            if hasattr(feature_fun, "is_feature") }
    @feature
    def log_population(self):
        return math.log(self.geoname['population'] + 1)
    @feature
    def name_count(self):
        # Geonames with lots of alternate names
        # tend to be the ones most commonly referred to.
        return self.geoname['name_count']
    @feature
    def num_spans(self):
        return len(self.geoname.spans)
    @feature
    def max_span_length(self):
        max_span_length = max([
            len(span.text) for span in self.geoname.spans
        ])
        return max_span_length
    @feature
    def cannonical_name_used(self):
        return 1 if any([
            span.text == self.geoname['name'] for span in self.geoname.spans
        ]) else 0
    @feature
    def NEs_contained(self):
        geoname = self.geoname
        NE_overlap = 0
        total_len = 0
        for span in geoname.spans:
            ne_spans = span.doc.tiers['nes'].spans_in_span(span)
            total_len += len(span.text)
            for ne_span in ne_spans:
                if ne_span.label == 'GPE':
                    NE_overlap += len(ne_span.text)
        return float(NE_overlap) / total_len
    @feature
    def ambiguity(self):
        return len(self.geoname.alternate_locations)
    @feature
    def PPL_feature_code(self):
        return 1 if self.geoname['feature_code'].startswith('PPL') else 0
    @feature
    def ADM_feature_code_score(self):
        return 1 if self.geoname['feature_code'].startswith('ADM') else 0
    @feature
    def CONT_feature_code(self):
        return 1 if self.geoname['feature_code'].startswith('CONT') else 0
    def to_dict(self):
        return self.feature_dict
    def values(self):
        result = []
        for key in sorted(self.feature_dict.keys()):
            result.append(self.feature_dict[key])
        return result

class GeonameAnnotator(Annotator):
    def __init__(self):
        self.connection = get_database_connection()
        self.connection.row_factory = GeonameRow
    def get_candidate_geonames(self, doc):
        """
        Returns an array of geoname dicts correponding to locations that the document may refer to.
        The dicts are extended with lists of associated AnnoSpans.
        """
        if 'ngrams' not in doc.tiers:
            ngram_annotator = NgramAnnotator()
            doc.add_tier(ngram_annotator)
        if 'nes' not in doc.tiers:
            ne_annotator = NEAnnotator()
            doc.add_tier(ne_annotator)
        logger.info('Named entities annotated')
        all_ngrams = list(set([span.text.lower()
            for span in doc.tiers['ngrams'].spans
            if span.text not in blocklist and
            # We can rule out a few FPs by only looking at capitalized names.
            span.text[0] == span.text[0].upper()
        ]))
        logger.info('%s ngrams extracted' % len(all_ngrams))
        cursor = self.connection.cursor()
        results  = cursor.execute('''
        SELECT
            geonames.*,
            count AS name_count,
            group_concat(alternatename, ";") AS names_used
        FROM geonames
        JOIN alternatename_counts USING ( geonameid )
        JOIN alternatenames USING ( geonameid )
        WHERE alternatename_lemmatized IN (''' +
        ','.join('?' for x in all_ngrams) +
        ''') GROUP BY geonameid''', all_ngrams)
        geoname_results = list(results)#[Geoname(result) for result in results]
        logger.info('%s geonames fetched' % len(geoname_results))
        # Associate spans with the geonames.
        # This is done up front so span information can be used in the scoring
        # function
        span_text_to_spans = {
            span.text.lower() : []
            for span in doc.tiers['ngrams'].spans
        }
        for span in doc.tiers['ngrams'].spans:
            span_text_to_spans[span.text.lower()].append(span)
        candidate_locations = []
        for geoname in geoname_results:
            geoname.add_spans(span_text_to_spans)
            candidate_locations.append(geoname)
        # Add combined spans to locations that are adjacent to a span linked to
        # an administrative division. e.g. Seattle, WA
        span_to_locations = {}
        for location in candidate_locations:
            for span in location.spans:
                span_to_locations[span] =\
                    span_to_locations.get(span, []) + [location]
        for span_a, span_b in itertools.permutations(
            list(span_to_locations.keys()), 2
        ):
            if not span_a.comes_before(span_b, max_dist=4): continue
            if (
                len(
                    set(span_a.doc.text[span_a.end:span_b.start]) - set(", ")
                ) > 1
            ): continue
            combined_span = span_a.extended_through(span_b)
            possible_locations = []
            for loc_a, loc_b in itertools.product(
                span_to_locations[span_a],
                span_to_locations[span_b],
            ):
                if(
                    loc_b['feature_code'].startswith('ADM') and
                    loc_a['feature_code'] != loc_b['feature_code']
                ):
                    if location_contains(loc_b, loc_a) > 0:
                        loc_a.spans.add(combined_span)
                        loc_a.parent_location = loc_b
        # Find locations with overlapping spans
        for idx, location_a in enumerate(candidate_locations):
            a_spans = location_a.spans
            for location_b in candidate_locations[idx + 1:]:
                b_spans = location_b.spans
                if len(a_spans & b_spans) > 0:
                    # Note that is is possible for two valid locations to have
                    # overlapping names. For example, Harare Province has
                    # Harare as an alternate name, so the city Harare is very
                    # to be an alternate location that competes with it.
                    location_a.alternate_locations.add(location_b)
                    location_b.alternate_locations.add(location_a)
        logger.info('%s candidate locations prepared' % len(candidate_locations))
        return candidate_locations
    def extract_features(self, locations):
        return [GeonameFeatures(location) for location in locations]
    def cull_geospans(self, geo_spans):
        mwis = find_maximum_weight_interval_set([
            Interval(
                geo_span.start,
                geo_span.end,
                # If the size is equal the score is used as a tie breaker.
                geo_span.size() + geo_span.geoname['score'],
                geo_span
            )
            for geo_span in geo_spans
        ])
        retained_spans = [interval.corresponding_object for interval in mwis]
        logger.info('overlapping geospans removed')
        return retained_spans
    def annotate(self, doc):
        logger.info('geoannotator started')
        candidate_locations = self.get_candidate_geonames(doc)
        features = self.extract_features(candidate_locations)
        for location, feature in zip(candidate_locations, features):
            location.score = predict_proba(
                [feature.values()])[0][1]
        culled_locations = [location
            for location in candidate_locations
            if location.score > 0.2]
        geo_spans = []
        for location in culled_locations:
            for span in location.spans:
                geo_span = GeoSpan(
                    span.start, span.end, doc, location.to_dict()
                )
                geo_spans.append(geo_span)
        culled_geospans = self.cull_geospans(geo_spans)
        doc.tiers['geonames'] = AnnoTier(culled_geospans)
        return doc
