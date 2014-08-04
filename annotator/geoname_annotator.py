#!/usr/bin/env python
"""Token Annotator"""
import math
import re
from collections import defaultdict

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

blocklist = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December',
             'International', 'North', 'East', 'West', 'South',
             'Eastern', 'Western', 'Southern', 'Northern',
             'About', 'Many', 'See', 'As', 'About', 'Center', 'Central',
             'City', 'World', 'University', 'Valley',
             # NIH could be legitimate, but rarely is it referred to in a context
             # where its location is relevent.
             'National Institutes of Health']

states = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}


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

        ngrams_by_lc = defaultdict(list)
        for ngram in all_ngrams:
            ngrams_by_lc[ngram.lower()] += ngram

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
            def __hash__(self):
                return id(self)

        remaining_locations = []
        for location_dict in geoname_results:
            location = Location(location_dict)
            location['spans'] = []
            location['alternateLocations'] = set()
            remaining_locations.append(location)
            geoname_results
            names = set([location['name']] + location['alternatenames'])
            for name in names:
                if name not in span_text_to_spans: continue
                for span in span_text_to_spans[name]:
                    location['spans'].append(span)
        # Find locations with overlapping spans
        for idx, location_a in enumerate(remaining_locations):
            a_spans = set(location_a['spans'])
            for idx, location_b in enumerate(remaining_locations[idx + 1:]):
                b_spans = set(location_b['spans'])
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
        resolved_locations = []
        THRESH = 60
        while True:
            for candidate in remaining_locations:
                candidate['score'] = self.score_candidate(
                    candidate, resolved_locations
                )
                # This is just for debugging, put FP and FN ids here to see
                # their score.
                if candidate['geonameid']  in ['888825']:
                    print (
                        candidate['name'],
                        candidate['spans'][0].text,
                        candidate['score']
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
            # These properties are removed because they
            # cannot be easily jsonified.
            location.pop('alternateLocations')
            location.pop('spans')

        retained_spans = []
        for geo_span_a in geo_spans:
            retain_a_overlap = True
            for geo_span_b in geo_spans:
                if geo_span_a == geo_span_b: continue
                if(
                    geo_span_b.start in range(geo_span_a.start, geo_span_a.end)
                    or
                    geo_span_a.start in range(geo_span_b.start, geo_span_b.end)
                ):
                    if geo_span_b.size() > geo_span_a.size():
                        # geo_span_a is probably a component of geospan b,
                        # e.g. Washington in University of Washington
                        # We use the longer span because it's usually correct.
                        retain_a_overlap = False
                    elif geo_span_b.size() == geo_span_a.size():
                        # Ambiguous name, use the scores to decide.
                        retain_a_overlap = geo_span_a.geoname['score'] >= geo_span_b.geoname['score']
            if not retain_a_overlap:
                continue
            # AFAICT the state town filter has no impact on the results
            #if not self.state_town_filter(geo_span_a, geo_spans): continue
            retained_spans.append(geo_span_a)
        
        doc.tiers['geonames'] = AnnoTier(retained_spans)

        return doc

    def state_town_filter(self, geo_span_a, geo_spans):
        """Check to see if we have a mention of the state for a city. If it's a
           small city and we don't have the state it belongs to in our set, it
           fails the test. Returns True if passes filter, False otherwise."""

        if ((geo_span_a.geoname['population'] > 100000) or
            (not "admin1 code" in geo_span_a.geoname) or
            (not geo_span_a.geoname["admin1 code"] in states)):
           return True # passes; doesn't have a state associated with it
        else:
            state = states[geo_span_a.geoname["admin1 code"]]
            all_names = [geo_span.geoname['name'] for geo_span in geo_spans]
            if state in all_names:
                return True
            else:
                return False

    def adjacent_state_filter(self, geo_span):
        """If we have "Fairview, OR" don't allow that to map to Fairview, MN"""

        if ((not "admin1 code" in geo_span.geoname) or
            (not geo_span.geoname["admin1 code"] in states)):
           return True # passes; doesn't have a state associated with it
        else:
            state = states[geo_span.geoname["admin1 code"]]
            next_span = geo_span.doc.tiers['geonames'].next_span(geo_span)
            if (next_span.geoname['name'] in states.values() and
                next_span.geoname['name'] != state):
                    return False
            else:
                return True

    def ne_filter(self, geo_span):
        """Check to see if this span overlaps with a named entity tag. Return
           True if not. If it does, return True if the NE is type GPE, else False."""

        ne_spans = geo_span.doc.tiers['nes'].spans_at_span(geo_span)

        if len(ne_spans) == 0:
            return True
        else:
            for ne_span in ne_spans:
                if ne_span.label == 'GPE':
                    return True
            return False

    def blocklist_filter(self, geo_span):
        if geo_span.geoname['name'] in blocklist:
            return False
        else:
            return True

    def score_candidate(self, candidate, resolved_locations):
        """
        Return a score between 0 and 100
        """
        def population_score():
            if candidate['population'] > 1000000:
                return 100
            elif candidate['population'] > 500000:
                return 50
            elif candidate['population'] > 100000:
                return 10
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

        def span_score():
            return min(100, len(candidate['spans']))

        def short_span_score():
            return min(100, 10 * len([
                span for span in candidate['spans']
                if len(span.text) < 4
            ]))

        def cannonical_name_used():
            return 100 if any([
                span.text == candidate['name'] for span in candidate['spans']
            ]) else 0

        def overlapping_NEs():
            score = 0
            for span in candidate['spans']:
                ne_spans = span.doc.tiers['nes'].spans_at_span(span)
                for ne_span in ne_spans:
                    if ne_span.label == 'GPE':
                        score += 30
            return min(100, score)

        def distinctiveness():
            return 100 / (len(candidate['alternateLocations']) + 1)
        
        def max_span():
            return len(max([span.text for span in candidate['spans']]))

        def close_locations():
            score = 0
            if resolved_locations:
                total_distance = 0.0
                for location in resolved_locations:
                    distance = great_circle(
                        (candidate['latitude'], candidate['longitude']),
                        (location['latitude'], location['longitude'])
                        ).kilometers
                    total_distance += distance
                    if distance < 10:
                        score += 100
                    elif distance < 20:
                        score += 50
                    elif distance < 30:
                        score += 20
                    elif distance < 50:
                        score += 10
                    elif distance < 500:
                        score += 5
                    elif distance < 1000:
                        score += 2
                average_distance = total_distance / len(resolved_locations)
                distance_score = average_distance / 100
            return score

        if candidate['population'] < 1000 and candidate['feature class'] in ['A', 'P']:
            return 0

        # Commented out features will not be evaluated.
        feature_weights = {
            population_score : 1.5,
            synonymity : 1.5,
            span_score : 0.2,
            short_span_score : (-4),
            overlapping_NEs : 1,
            distinctiveness : 1,
            max_span : 1,
            close_locations : 1,
            cannonical_name_used : 0.5,
        }
        return sum([
            score_fun() * float(weight)
            for score_fun, weight in feature_weights.items()
        ]) / math.sqrt(sum([x**2 for x in feature_weights.values()]))
