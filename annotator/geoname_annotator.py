#!/usr/bin/env python
"""Token Annotator"""

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
             'About', 'Many', 'See', 'As', 'About', 'Center', 'University', 'Valley']

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

        all_ngrams = set([span.label
                          for span in doc.tiers['ngrams'].spans])

        ngrams_by_lc = defaultdict(list)
        for ngram in all_ngrams:
            ngrams_by_lc[ngram.lower()] += ngram

        geoname_cursor = self.geonames_collection.find({
            'name' : { '$in' : list(all_ngrams) }
        })
        geoname_results = list(geoname_cursor)

        candidates_by_name = defaultdict(list)
        for location in geoname_results:
            candidates_by_name[location['name']].append(location)

        # iterative resolution
        resolved_locations_by_name = {}
        rejected_locations_by_name = {}
        delete_queue = []
        round_id = 0

        previous_length = 999

        while len(resolved_locations_by_name) != previous_length:
            round_id += 1

            previous_length = len(resolved_locations_by_name)

            for location_name in delete_queue:
                del(candidates_by_name[location_name])
            delete_queue = []

            for location_name, candidates in candidates_by_name.iteritems():
                scored_candidates = [
                    (self.score_candidate(candidate, resolved_locations_by_name.values()), candidate)
                    for candidate in candidates
                    ]
                sorted_candidates = sorted(scored_candidates, reverse=True)
                if sorted_candidates[0][0] >= 30 or (len(scored_candidates) <= 2 and sorted_candidates[0][0] >= 20):
                    resolved_locations_by_name[location_name] = sorted_candidates[0][1]
                    rejected_locations_by_name[location_name] = sorted_candidates[1:]

                    delete_queue.append(location_name)
                    next


        geo_spans = []
        for span in doc.tiers['ngrams'].spans:
            if span.label in resolved_locations_by_name:
                location = resolved_locations_by_name[span.label]
                label = location['name']
                geo_span = AnnoSpan(span.start, span.end,
                                    doc,
                                    label=label)
                geo_span.geoname = location
                geo_spans.append(geo_span)

        retained_spans = []
        for geo_span_a in geo_spans:
            retain_a_overlap = True
            for geo_span_b in geo_spans:
                if (((geo_span_b.start in range(geo_span_a.start, geo_span_a.end)) or
                    (geo_span_a.start in range(geo_span_b.start, geo_span_b.end))) and
                    geo_span_b.size() >= geo_span_a.size() and
                    geo_span_a != geo_span_b):
                    retain_a_overlap = False

            if (retain_a_overlap and
                self.state_town_filter(geo_span_a, geo_spans) and
                self.blocklist_filter(geo_span_a) and
                self.ne_filter(geo_span_a)):
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
        if candidate['population'] > 1000000:
            population_score = 100
        elif candidate['population'] > 500000:
            population_score = 50
        elif candidate['population'] > 100000:
            population_score = 10
        elif candidate['population'] > 10000:
            population_score = 5
        else:
            population_score = 0

        close_locations = 0
        if resolved_locations:
            total_distance = 0.0
            for location in resolved_locations:
                distance = great_circle(
                    (candidate['latitude'], candidate['longitude']),
                    (location['latitude'], location['longitude'])
                    ).kilometers
                total_distance += distance
                if distance < 10:
                    close_locations += 100
                elif distance < 20:
                    close_locations += 50
                elif distance < 30:
                    close_locations += 20
                elif distance < 50:
                    close_locations += 10
                elif distance < 500:
                    close_locations += 5
                elif distance < 1000:
                    close_locations += 2

            average_distance = total_distance / len(resolved_locations)
            distance_score = average_distance / 100

        if candidate['population'] < 1000 and candidate['feature class'] in ['A', 'P']:
            return 0
        else:
            return population_score + close_locations

