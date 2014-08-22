#!/usr/bin/env python
"""Token Annotator"""
import math
import re
import itertools
import pymongo

from annotator import *
from ngram_annotator import NgramAnnotator
from ne_annotator import NEAnnotator
from geopy.distance import great_circle

def geoname_matches_original_ngram(geoname, original_ngrams):
    if (geoname['name'] in original_ngrams):
        return True
    else:
        for original_ngram in original_ngrams:
            if original_ngram in geoname['alternatenames']:
                return True

    return False

# TODO: We might be able to remove some of these names in a more general way
# by adding a feature to the scoring function.
blocklist = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July',
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'August', 'September', 'October', 'November', 'December',
    'North', 'East', 'West', 'South',
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
    0 indicates no containment.
    This is not guarenteed to be correct, it is based on my assumptions
    about the geonames heirarchy.
    """
    if not loc_outer['feature class'].startswith('ADM'):
        # I don't think admin codes are comparable in this case,
        # so just use the country code.
        return loc_outer['country code'] == loc_inner['country code']
    props = [
        'country code',
        'admin1 code',
        'admin2 code',
        'admin3 code',
        'admin4 code'
    ]
    for idx, prop in enumerate(props):
        if len(loc_outer[prop]) == 0:
            return idx
        if loc_outer[prop] != loc_inner[prop]:
            return 0
    return len(props)

class GeonameAnnotator(Annotator):

    def __init__(self, geonames_collection=None):
        if not geonames_collection:
            db = pymongo.Connection('localhost', port=27017)['geonames']
            geonames_collection = db.allCountries
        self.geonames_collection = geonames_collection

    # TODO text in this case means AnnoText, elswhere, it's raw text
    def annotate(self, doc):

        if 'ngrams' not in doc.tiers:
            ngram_annotator = NgramAnnotator()
            doc.add_tier(ngram_annotator)
            ne_annotator = NEAnnotator()
            doc.add_tier(ne_annotator)

        all_ngrams = set([span.text
            for span in doc.tiers['ngrams'].spans
            if span.text not in blocklist and
            # We can rule out a few FPs by only looking at capitalized names.
            span.text[0] == span.text[0].upper()
        ])

        geoname_cursor = self.geonames_collection.find({
            '$or' : [
                { 'name' : { '$in' : list(all_ngrams) } },
                # I suspect using multiple indecies slows this
                # query down by a factor of two. It might be worthwhile
                # to add name to alternate names so we can just
                # search on that property.
                { 'alternatenames' : { '$in' : list(all_ngrams) } }
            ]
        })
        geoname_results = list(geoname_cursor)

        # ObjectId() cannot be JSON serialized and we have no use for them
        for geoname_result in geoname_results:
            del geoname_result['_id']

        # Associate spans with the geonames.
        # This is done up front so span information can be used in the scoring
        # function
        span_text_to_spans = {
            span.text : []
            for span in doc.tiers['ngrams'].spans
        }
        for span in doc.tiers['ngrams'].spans:
            span_text_to_spans[span.text].append(span)
        class Location(dict):
            """
            This main purpose of this class is to create hashable dictionaries
            that we can use in sets.
            """
            def __hash__(self):
                return id(self)

        candidate_locations = []
        for location_dict in geoname_results:
            location = Location(location_dict)
            location['spans'] = set()
            location['alternateLocations'] = set()
            candidate_locations.append(location)
            geoname_results
            names = set([location['name']] + location['alternatenames'])
            for name in names:
                if name not in span_text_to_spans: continue
                for span in span_text_to_spans[name]:
                    location['spans'].add(span)
                    
        # Add combined spans to locations that are adjacent to a span linked to
        # an administrative division. e.g. Seattle, WA
        span_to_locations = {}
        for location in candidate_locations:
            for span in location['spans']:
                span_to_locations[span] =\
                    span_to_locations.get(span, []) + [location]
        for span_a, span_b in itertools.permutations(
            span_to_locations.keys(), 2
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
                # print 'loc:', loc_a['name'], loc_b['name'], loc_b['feature code']
                if(
                    loc_b['feature code'].startswith('ADM') and
                    loc_a['feature code'] != loc_b['feature code']
                ):
                    if location_contains(loc_b, loc_a) > 0:
                        loc_a['spans'].add(combined_span)
                        loc_a['parentLocation'] = loc_b
        
        # Find locations with overlapping spans
        for idx, location_a in enumerate(candidate_locations):
            a_spans = location_a['spans']
            for idx, location_b in enumerate(candidate_locations[idx + 1:]):
                b_spans = location_b['spans']
                if len(a_spans & b_spans) > 0:
                    # Note that is is possible for two valid locations to have
                    # overlapping names. For example, Harare Province has
                    # Harare as an alternate name, so the city Harare is very
                    # to be an alternate location that competes with it.
                    location_a['alternateLocations'].add(location_b)
                    location_b['alternateLocations'].add(location_a)
        # Iterative resolution
        # Add location with scores above the threshold to the resolved location.
        # Keep rescoring the remaining locations until no more can be resolved.
        remaining_locations = list(candidate_locations)
        resolved_locations = []
        THRESH = 60
        iteration = 0
        while True:
            # print "iteration:", iteration
            iteration += 1
            for candidate in remaining_locations:
                candidate['score'] = self.score_candidate(
                    candidate, resolved_locations
                )

            # If there are alternate locations with higher scores
            # give this candidate a zero.
            for candidate in remaining_locations:
                for alt in candidate['alternateLocations']:
                    # We end up with multiple locations for per span if they
                    # are resolved in different iterations or
                    # if the scores are exactly the same.
                    # TODO: This needs to be delt with in the next stage.
                    if candidate['score'] < alt['score']:
                        candidate['score'] = 0
                        break

            newly_resolved_candidates = [
                candidate
                for candidate in remaining_locations
                if candidate['score'] > THRESH
            ]
            resolved_locations.extend(newly_resolved_candidates)
            for candiate in newly_resolved_candidates:
                if candidate in remaining_locations:
                    remaining_locations.remove(candiate)
            if len(newly_resolved_candidates) == 0:
                break

        geo_spans = []
        for location in resolved_locations:
            # Copy the dict so we don't need to return a custom class.
            location = dict(location)
            for span in location['spans']:
                # Maybe we should try to rule out some of the spans that
                # might not actually be associated with the location.
                geo_span = AnnoSpan(
                    span.start, span.end, doc, label=location['name']
                )
                geo_span.geoname = location
                geo_spans.append(geo_span)

        retained_spans = []
        for geo_span_a in geo_spans:
            retain_a_overlap = True
            for geo_span_b in geo_spans:
                if geo_span_a == geo_span_b: continue
                if geo_span_a.overlaps(geo_span_b):
                    if geo_span_b.size() > geo_span_a.size():
                        # geo_span_a is probably a component of geospan b,
                        # e.g. Washington in University of Washington
                        # We use the longer span because it's usually correct.
                        retain_a_overlap = False
                        break
                    elif geo_span_b.size() == geo_span_a.size():
                        # Ambiguous name, use the scores to decide.
                        # TODO: Recompute scores since they could have been
                        # resolved in different rounds.
                        if geo_span_a.geoname['score'] < geo_span_b.geoname['score']:
                            retain_a_overlap = False
                            break
            if not retain_a_overlap:
                continue
            retained_spans.append(geo_span_a)

        # Remove unneeded properties:
        # Be careful if adding these back in, they might not be serializable
        # data types.
        props_to_omit = ['spans', 'alternateLocations', 'alternatenames']
        for geospan in geo_spans:
            # The while loop removes the properties from the parentLocations.
            # There will probably only be one parent location.
            cur_location = geospan.geoname
            while True:
                if all([
                    prop not in cur_location
                    for prop in props_to_omit
                ]):
                    break
                for prop in props_to_omit:
                    cur_location.pop(prop)
                if 'parentLocation' in cur_location:
                    cur_location = cur_location['parentLocation']
                else:
                    break

        doc.tiers['geonames'] = AnnoTier(retained_spans)

        return doc

    def score_candidate(self, candidate, resolved_locations):
        """
        Return a score between 0 and 100
        """
        def population_score():
            if candidate['population'] > 1000000:
                return 100
            elif candidate['population'] > 500000:
                return 60
            elif candidate['population'] > 300000:
                return 40
            elif candidate['population'] > 200000:
                return 30
            elif candidate['population'] > 100000:
                return 20
            elif candidate['population'] > 10000:
                return 5
            else:
                return 0

        def synonymity():
            # Geonames with lots of alternate names
            # tend to be the ones most commonly referred to.
            # For examle, coutries have lots of alternate names.
            if len(candidate['alternatenames']) > 8:
                return 100
            elif len(candidate['alternatenames']) > 4:
                return 50
            elif len(candidate['alternatenames']) > 0:
                return 10
            else:
                return 0

        def num_spans_score():
            return min(len(candidate['spans']), 4) * 25

        def short_span_score():
            max_span_length = max([
                len(span.text) for span in candidate['spans']
            ])
            if max_span_length < 4:
                return 100
            elif max_span_length < 5:
                return 10
            else:
                return 0

        def cannonical_name_used():
            return 100 if any([
                span.text == candidate['name'] for span in candidate['spans']
            ]) else 0

        def NEs_contained():
            NE_overlap = 0
            total_len = 0
            for span in candidate['spans']:
                ne_spans = span.doc.tiers['nes'].spans_in_span(span)
                total_len += len(span.text)
                for ne_span in ne_spans:
                    if ne_span.label == 'GPE':
                        NE_overlap += len(ne_span.text)
            return float(100 * NE_overlap) / total_len

        def distinctness():
            return 100 / float(len(candidate['alternateLocations']) + 1)
        
        def max_span_score():
            max_span = max([
                len(span.text) for span in candidate['spans']
            ])
            if max_span < 5: return 0
            elif max_span < 8: return 40
            elif max_span < 10: return 60
            elif max_span < 15: return 80
            else: return 100

        def close_locations():
            if len(resolved_locations) == 0: return 0
            count = 0
            for location in resolved_locations:
                distance = great_circle(
                    (candidate['latitude'], candidate['longitude']),
                    (location['latitude'], location['longitude'])
                ).kilometers
                if distance < 500:
                    count += 1
            return 100 * float(count) / len(resolved_locations)
            
        def closest_location():
            if len(resolved_locations) == 0: return 0
            closest = min([
                great_circle(
                    (candidate['latitude'], candidate['longitude']),
                    (location['latitude'], location['longitude'])
                ).kilometers
                for location in resolved_locations
            ])
            if closest < 10:
                return 100
            elif closest < 100:
                return 60
            elif closest < 1000:
                return 40
            else:
                return 0
            
        def containment_level():
            max_containment_level = max([
                max(
                    location_contains(location, candidate),
                    location_contains(candidate, location)
                )
                for location in resolved_locations
            ] + [0])
            if max_containment_level == 0:
                return 0
            else:
                return 40 + max_containment_level * 10
            
        def feature_code_score():
            for code, score in {
                # Continent (need this bc Africa has 0 population)
                'CONT' : 100,
                'ADM' : 80,
                'PPL' : 65,
            }.items():
                if candidate['feature code'].startswith(code):
                    return score
            return 0
        
        # This prevents us from picking up congo town
        # if candidate['population'] < 1000 and candidate['feature class'] in ['A', 'P']:
        #     return 0

        if any([
            alt in resolved_locations
            for alt in candidate['alternateLocations']
        ]):
            return 0

        # Commented out features will not be evaluated.
        feature_weights = {
            population_score : 2.0,
            synonymity : 1.0,
            num_spans_score : 0.4,
            short_span_score : (-5),
            NEs_contained : 1.2,
            # Distinctness is probably more effective when combined
            # with other features
            distinctness : 1.0,
            max_span_score : 1.0,
            close_locations : 0.8,
            closest_location : 0.8,
            containment_level : 0.8,
            cannonical_name_used : 0.5,
            feature_code_score : 0.6,
        }
        total_score = sum([
            score_fun() * float(weight)
            for score_fun, weight in feature_weights.items()
        ]) / math.sqrt(sum([x**2 for x in feature_weights.values()]))
        
        # This is just for debugging, put FP and FN ids here to see
        # their score.
        if candidate['geonameid'] in ['372299', '8060879', '408664', '377268']:
            print (
                candidate['name'],
                list(candidate['spans'])[0].text,
                total_score
            )
            print {
                score_fun.__name__ : score_fun()
                for score_fun, weight in feature_weights.items()
            }
        
        return total_score
