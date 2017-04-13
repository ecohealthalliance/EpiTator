#!/usr/bin/env python
"""Geoname Annotator"""
import math
import re
import itertools
import sqlite3
from collections import defaultdict
from lazy import lazy

from annotator import Annotator, AnnoDoc, AnnoTier, AnnoSpan
from ngram_annotator import NgramAnnotator
from ne_annotator import NEAnnotator
from geopy.distance import great_circle
from maximum_weight_interval_set import Interval, find_maximum_weight_interval_set

from get_database_connection import get_database_connection
import math
import geoname_classifier

import datetime
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

blocklist = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'August', 'September', 'October', 'November', 'December',
    'North', 'East', 'West', 'South',
    'Northeast', 'Southeast', 'Northwest', 'Southwest',
    'Eastern', 'Western', 'Southern', 'Northern',
    'About', 'Many', 'See', 'Also', 'As', 'About', 'Health',
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
    Do a comparison to see if the first geoname contains the second.
    It returns an integer to indicate the level of containment.
    0 indicates no containment. Siblings locations and identical locations
    have 0 containment. The level of containment is determined by the specificty
    of the outer location. e.g. USA would be a smaller number than Texas.
    In order for containment to be detected the outer location must have a
    ADM* or PCL* feature code, which is most countries, states, and districts.
    """
    props = [
        'country_code',
        'admin1_code',
        'admin2_code',
        'admin3_code',
        'admin4_code'
    ]
    if loc_outer['geonameid'] == loc_inner['geonameid']:
        return 0
    if re.match("^PCL.", loc_outer['feature_code']):
        outer_feature_level = 1
    elif loc_outer['feature_code'] == 'ADM1':
        outer_feature_level = 2
    elif loc_outer['feature_code'] == 'ADM2':
        outer_feature_level = 3
    elif loc_outer['feature_code'] == 'ADM3':
        outer_feature_level = 4
    elif loc_outer['feature_code'] == 'ADM4':
        outer_feature_level = 5
    else:
        return 0
    for prop in props[:outer_feature_level]:
        if loc_outer[prop] == '':
            return 0
        if loc_outer[prop] != loc_inner[prop]:
            return 0
    return outer_feature_level

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
    @lazy
    def lat_long(self):
        return (self['latitude'], self['longitude'])
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

class GeonameFeatures(object):
    """
    This represents the aspects of a condidate geoname that are used to
    determine whether it is being referenced.
    """
    # The feature name array is used to maintain the order of the
    # values in the feature vector.
    feature_names = [
        'log_population',
        'name_count',
        'num_spans',
        'max_span_length',
        'cannonical_name_used',
        'loc_NE_portion',
        'other_NE_portion',
        'ambiguity',
        'PPL_feature_code',
        'ADM_feature_code_score',
        'CONT_feature_code',
        'other_feature_code',
        # contextual features
        'close_locations',
        'containing_locations',
        'max_containment_level',
        # This is inverted so a zero from undefined contextual features
        # doesn't boost the score.
        'inv_closest_location_distance_km',
        # high_confidence indicates the base feature set received a high score.
        # It is an useful feature for preventing high confidence geonames
        # from receiving low final scores when they lack contextual cues -
        # for example, when they are the only location mentioned.
        'high_confidence',
    ]
    def __init__(self, geoname, spans_to_nes):
        self.geoname = geoname
        # The set of geonames that are mentioned in proximity to the spans
        # corresponding to this feature.
        # This will be populated by the add_contextual_features function.
        self.nearby_mentions = set()
        d = {}
        d['log_population'] = math.log(geoname['population'] + 1)
        # Geonames with lots of alternate names
        # tend to be the ones most commonly referred to.
        d['name_count'] = geoname['name_count']
        d['num_spans'] = len(geoname.spans)
        d['max_span_length'] = max([
            len(span.text) for span in geoname.spans])
        d['cannonical_name_used'] = 1 if any([
            span.text == geoname['name'] for span in geoname.spans
        ]) else 0
        loc_NEs_overlap = 0
        other_NEs_overlap = 0
        total_len = len(geoname.spans)
        for span in geoname.spans:
            for ne_span in spans_to_nes[span]:
                if ne_span.label == 'GPE' or ne_span.label == 'LOC':
                    loc_NEs_overlap += 1
                else:
                    other_NEs_overlap += 1
        d['loc_NE_portion'] = float(loc_NEs_overlap) / total_len
        d['other_NE_portion'] = float(other_NEs_overlap) / total_len
        d['ambiguity'] = len(geoname.alternate_locations)
        feature_code = geoname['feature_code']
        if feature_code.startswith('PPL'):
            d['PPL_feature_code'] = 1
        elif feature_code.startswith('ADM'):
            d['ADM_feature_code_score'] = 1
        elif feature_code.startswith('CONT'):
            d['CONT_feature_code'] = 1
        else:
            d['other_feature_code'] = 1
        self._values = [0] * len(self.feature_names)
        self.set_values(d)
    def set_value(self, feature_name, value):
        self._values[self.feature_names.index(feature_name)] = value
    def set_values(self, value_dict):
        for idx, name in enumerate(self.feature_names):
            if name in value_dict:
                self._values[idx] = value_dict[name]
    def set_contextual_features(self):
        """
        GeonameFeatures are initialized with only values that can be extracted
        from the geoname database and span. This extends the GeonameFeature
        with values that require information from nearby_mentions.
        """
        geoname = self.geoname
        close_locations = 0
        inv_closest_location_distance_km = 0
        containing_locations = 0
        max_containment_level = 0
        for recently_mentioned_geoname in self.nearby_mentions:
            if recently_mentioned_geoname == geoname:
                continue
            containment_level = max(
                location_contains(geoname, recently_mentioned_geoname),
                location_contains(recently_mentioned_geoname, geoname))
            if containment_level > 0:
                containing_locations += 1
            if containment_level > max_containment_level:
                max_containment_level = containment_level
            distance = great_circle(
                recently_mentioned_geoname.lat_long, geoname.lat_long
            ).kilometers
            if distance < 1.0:
                inv_distance = 1.0
            else:
                inv_distance = 1.0 / distance
            if inv_distance > inv_closest_location_distance_km:
                inv_closest_location_distance_km = inv_distance
            if distance < 500:
                close_locations += 1
        self.set_values(dict(
            close_locations=close_locations,
            containing_locations=containing_locations,
            max_containment_level=max_containment_level,
            inv_closest_location_distance_km=inv_closest_location_distance_km))
    def to_dict(self):
        return {
            key: value
            for key, value in zip(self.feature_names, self._values)}
    def values(self):
        return self._values

class GeonameAnnotator(Annotator):
    def __init__(self, custom_classifier=None):
        self.connection = get_database_connection()
        self.connection.row_factory = GeonameRow
        if custom_classifier:
            self.geoname_classifier = custom_classifier
        else:
            self.geoname_classifier = geoname_classifier
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
        geoname_results = list(cursor.execute('''
        SELECT
            geonames.*,
            count AS name_count,
            group_concat(alternatename, ";") AS names_used
        FROM geonames
        JOIN alternatename_counts USING ( geonameid )
        JOIN alternatenames USING ( geonameid )
        WHERE alternatename_lemmatized IN (''' +
        ','.join('?' for x in all_ngrams) +
        ''') GROUP BY geonameid''', all_ngrams))
        logger.info('%s geonames fetched' % len(geoname_results))
        # Associate spans with the geonames.
        # This is done up front so span information can be used in the scoring
        # function
        span_text_to_spans = defaultdict(list)
        for span in doc.tiers['ngrams'].spans:
            span_text_to_spans[span.text.lower()].append(span)
        candidate_geonames = []
        for geoname in geoname_results:
            geoname.add_spans(span_text_to_spans)
            candidate_geonames.append(geoname)
        # Add combined spans to locations that are adjacent to a span linked to
        # an administrative division. e.g. Seattle, WA
        span_to_geonames = defaultdict(list)
        for geoname in candidate_geonames:
            for span in geoname.spans:
                span_to_geonames[span].append(geoname)
        geoname_spans = sorted(span_to_geonames.keys())
        for span_a_idx, span_a in enumerate(geoname_spans):
            span_b_idx = span_a_idx
            # There could be multiple overlapping spans that come after
            # this span. This loop will add combined spans for all of them.
            while True:
                # skip spans that overlap the first span
                while span_b_idx < len(geoname_spans) and geoname_spans[span_b_idx].start < span_a.end:
                    span_b_idx += 1
                if span_b_idx >= len(geoname_spans):
                    break
                span_b = geoname_spans[span_b_idx]
                span_b_idx += 1
                if not span_a.comes_before(span_b, max_dist=4):
                    break
                # If is more than one non-space/comma character between
                # the spans do not combine them.
                if (len(
                        set(span_a.doc.text[span_a.end:span_b.start]) - set(", ")
                    ) > 1): break
                combined_span = span_a.extended_through(span_b)
                for loc_a, loc_b in itertools.product(
                    span_to_geonames[span_a],
                    span_to_geonames[span_b]):
                    if location_contains(loc_b, loc_a) > 0:
                        loc_a.spans.add(combined_span)
                        span_to_geonames[combined_span].append(loc_a)
                        # TODO: Different parents could be used. Remove this property?
                        loc_a.parent_location = loc_b
        logger.info('%s combined spans added' % (
            len(span_to_geonames) - len(geoname_spans)))
        # Find locations with overlapping spans
        # Note that is is possible for two valid locations to have
        # overlapping names. For example, Harare Province has
        # Harare as an alternate name, so the city Harare is very
        # likely to be an alternate location that competes with it.
        for span, geonames in span_to_geonames.items():
            geoname_set = set(geonames)
            for geoname in geonames:
                geoname.alternate_locations |= geoname_set
        for geoname in candidate_geonames:
            geoname.alternate_locations -= set([geoname])
        logger.info('%s alternative locations found' % sum([
            len(geoname.alternate_locations) for geoname in candidate_geonames]))
        logger.info('%s candidate locations prepared' % len(candidate_geonames))
        return candidate_geonames
    def extract_features(self, geonames, doc):
        spans_to_nes = {}
        geospan_tier = AnnoTier(set([span for geoname in geonames for span in geoname.spans]))
        for span, ne_spans in geospan_tier.group_spans_by_containing_span(
            doc.tiers['nes'], allow_partial_containment=True):
            spans_to_nes[span] = ne_spans
        return [GeonameFeatures(geoname, spans_to_nes) for geoname in geonames]
    def add_contextual_features(self, features):
        """
        Extend a list of features with values that are based on the geonames
        mentioned nearby.
        """
        logger.info('adding contextual features')
        span_to_features = defaultdict(list)
        for feature in features:
            for span in feature.geoname.spans:
                span_to_features[span].append(feature)
        geoname_span_tier = AnnoTier(span_to_features.keys())
        def feature_generator(filter_fun=lambda x:True):
            for span in geoname_span_tier.spans:
                for feature in span_to_features[span]:
                    if filter_fun(feature):
                        yield span.start, feature
        # Create iterators that will cycle through all the spans returning the span
        # offset and the associated feature.
        all_feature_span_iter = feature_generator()
        resolved_feature_span_iter = feature_generator(lambda x: x.geoname.high_confidence)
        # boolean indicators of whether the corresponding iterator has reached its end.
        afs_iter_end = False
        rfs_iter_end = False
        # The starting index of the of the current feature span or resolved feature span.
        f_start = 0
        rf_start = 0
        # A ring buffer containing the recently mentioned resolved geoname features.
        rf_buffer = []
        rf_buffer_idx = 0
        BUFFER_SIZE = 10
        # The number of characters to lookahead searching for nearby mentions.
        LOOKAHEAD_OFFSET = 50
        # Fill the buffer to capacity with initially mentioned resolved features.
        while len(rf_buffer) < BUFFER_SIZE:
            try:
                rf_start, feature = next(resolved_feature_span_iter)
                rf_buffer.append(feature.geoname)
            except StopIteration:
                rfs_iter_end = True
                break
        # Iterate over all the feature spans and add the resolved features
        # in the ring buffer to the nearby_mentions set.
        while not afs_iter_end:
            while rfs_iter_end or f_start < rf_start - LOOKAHEAD_OFFSET:
                try:
                    f_start, feature = next(all_feature_span_iter)
                except StopIteration:
                    afs_iter_end = True
                    break
                feature.nearby_mentions.update(rf_buffer)
            try:
                rf_start, resolved_feature = next(resolved_feature_span_iter)
                rf_buffer[rf_buffer_idx % BUFFER_SIZE] = resolved_feature.geoname
                rf_buffer_idx += 1
            except StopIteration:
                rfs_iter_end = True
        for feature in features:
            feature.set_contextual_features()
    def cull_geospans(self, geo_spans):
        mwis = find_maximum_weight_interval_set([
            Interval(
                geo_span.start,
                geo_span.end,
                # If the size is equal the score is used as a tie breaker.
                geo_span.size() + geo_span.geoname.score,
                geo_span
            )
            for geo_span in geo_spans
        ])
        retained_spans = [interval.corresponding_object for interval in mwis]
        logger.info('overlapping geospans removed')
        return retained_spans
    def annotate(self, doc):
        logger.info('geoannotator started')
        candidate_geonames = self.get_candidate_geonames(doc)
        features = self.extract_features(candidate_geonames, doc)
        if len(features) == 0:
            doc.tiers['geonames'] = AnnoTier([])
            return doc
        scores = self.geoname_classifier.predict_proba_base([
            f.values() for f in features])
        for geoname, feature, score in zip(candidate_geonames, features, scores):
            geoname.high_confidence = float(score[1]) > self.geoname_classifier.HIGH_CONFIDENCE_THRESHOLD
            feature.set_value('high_confidence', geoname.high_confidence)
        self.add_contextual_features(features)
        scores = self.geoname_classifier.predict_proba_contextual([
            f.values() for f in features])
        for geoname, score in zip(candidate_geonames, scores):
            geoname.score = float(score[1])
        culled_geonames = [geoname
            for geoname in candidate_geonames
            if geoname.score > self.geoname_classifier.GEONAME_SCORE_THRESHOLD]
        geo_spans = []
        for geoname in culled_geonames:
            for span in geoname.spans:
                geo_span = GeoSpan(
                    span.start, span.end, doc, geoname)
                geo_spans.append(geo_span)
        culled_geospans = self.cull_geospans(geo_spans)
        doc.tiers['geonames'] = AnnoTier(culled_geospans)
        return doc
