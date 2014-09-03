#!/usr/bin/env python
"""
Annotates patient descriptions.
"""
import re
from collections import defaultdict

from annotator import *
import result_aggregators as ra
import utils

def process_match_dict(d):
    numeric_keys = ['number', 'min', 'max', 'range_start', 'range_end']
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = process_match_dict(v)
        elif hasattr(v, 'keyword_object'):
            d[k] = v.keyword_object
        elif k in numeric_keys:
            # Check for None?
            d[k] = utils.parse_spelled_number(v.string)
        else:
            d[k] = True
    return d

class KeypointSpan(AnnoSpan):
    def __init__(self, kp_match, doc):
        offsets_tuple = doc.find_match_offsets(kp_match)
        self.start = offsets_tuple[0]
        self.end = offsets_tuple[1]
        self.doc = doc
        self.label = kp_match.string
        metadata = process_match_dict(kp_match.groupdict())
        metadata['text'] = kp_match.string
        self.metadata = metadata
        self.__match__ = kp_match
    def to_dict(self):
        result = super(KeypointSpan, self).to_dict()
        result.update(self.metadata)
        return result

class PatientInfoAnnotator(Annotator):

    def annotate(self, doc, keyword_categories={}):
        """
        Annotate patient descriptions that appear in the doc.

        Keywords under keyword_categories that appear in the document are added
        to the patient descriptions under attributes corresponding to their
        categories.
        """
        doc.setup_pattern()
        my_search = doc.p_search
        numbers = my_search('{CD+ and? CD? CD?}')
        number_ranges = ra.follows([
            ('range_start', numbers),
            my_search('-|to|and|or'),
            ('range_end', numbers)
        ], max_words_between=2, max_overlap=0)
        min_number = ra.follows([
            my_search('GREATER|ABOVE|OVER|LEAST|MINIMUM|DOWN|EXCEED'),
            ('min', numbers)
        ], 3)
        max_number = ra.follows([
            my_search('LESS|BELOW|UNDER|MOST|MAXIMUM|UP'),
            ('max', numbers)
        ], 3)
        quantities = ra.combine([
            number_ranges,
            min_number,
            max_number,
            ra.label('number', numbers)
        ])
        approx_quantities = ra.near([
            ('approximate', my_search('APPROXIMATELY|ABOUT|NEAR|AROUND')),
            quantities
        ], 4)
        maybe_approx_quantities = ra.combine([
            approx_quantities, quantities
        ])
        time_quantities = ra.combine([
            ra.follows([
                maybe_approx_quantities, ('year_units', my_search('YEAR'))
            ]),
            ra.follows([
                maybe_approx_quantities, ('month_units', my_search('MONTH'))
            ])
        ], prefer='match_length')

        age_quantities = (
            ra.near([
                time_quantities,
                my_search('AGE|OLD')
            ], 1) +
            # E.x. in the age group of approximately 1 - 14
            ra.follows([
                my_search('AGE *? OF'),
                ra.combine([
                    time_quantities,
                    maybe_approx_quantities
                ])
            ], 1)
        )
        age_qualities = (
            ra.label('child', my_search('CHILD')) +
            ra.label('adult', my_search('ADULT')) +
            ra.label('senior', my_search('ELDER') + my_search('SENIOR CITIZEN'))
        )
        age_description = ra.label('age', ra.combine([
            age_quantities,
            age_qualities
        ]))
        patient_sex = (
            ra.label('female', my_search("WOMAN|FEMALE|GIRL")) +
            ra.label('male', my_search("MAN|MALE|BOY"))
        )
        keyword_attributes = []
        for cat, kws in keyword_categories.items():
            category_results = []
            for kw in kws:
                if isinstance(kw, basestring):
                    for match in my_search(pattern.search.escape(kw)):
                        match.keyword_object = kw
                        category_results.append(match)
                elif isinstance(kw, dict):
                    match = doc.byte_offsets_to_pattern_match(kw['offsets'][0])
                    match.keyword_object = kw
                    category_results.append(match)
                elif isinstance(kw, AnnoSpan):
                    match = doc.byte_offsets_to_pattern_match((kw.start, kw.end))
                    match.keyword_object = kw.to_dict()
                    category_results.append(match)
                else:
                    raise Exception(
                        "Unknown keyword datatype for: " + str(kws[0])
                    )
            keyword_attributes += [ra.label(cat, category_results)]
        quantity_modifiers = (
            ra.label('average', my_search('AVERAGE|MEAN')) +
            ra.label('annual', my_search('ANNUAL|ANNUALLY')) +
            ra.label('monthly', my_search('MONTHLY')) +
            ra.label('weekly', my_search('WEEKLY')) +
            ra.label('cumulative', my_search('TOTAL|CUMULATIVE|ALREADY')) +
            ra.label('incremental', my_search('NEW|ADDITIONAL|RECENT'))
        )
        all_quantities = ra.combine([
            ra.near([
                quantity_modifiers,
                maybe_approx_quantities
            ], 2),
            maybe_approx_quantities
        ], prefer='match_length')
        person = my_search('PERSON|CHILD|ADULT|ELDER|PATIENT|LIFE')
        report_type = map(utils.restrict_match, (
            ra.label('death',
                my_search('DIED|DEATH|FATALITIES|KILLED')
            ) +
            ra.label('hospitalization',
                my_search('HOSPITAL|HOSPITALIZED')
            ) +
            ra.label('case',
                my_search(
                    'CASE|INFECTION|INFECT|STRICKEN'
                ) + person
            )
        ))
        report_type = ra.combine([
            report_type,
            #Remove matches like "group of X"
            ra.follows([my_search('!NUMBER of'), report_type], max_overlap=1)
        ], remove_conflicts=True)
        report_description = ra.combine([
            ra.near([report_type, report_type], 2),
            report_type,
        ])
        number_description = ra.combine([
            ra.follows([
                quantity_modifiers,
                my_search('NUMBER')
            ]),
            my_search('NUMBER')
        ])
        people_quantity = ra.follows([
            all_quantities,
            person
        ], 2)
        case_count = ra.label('count',
            ra.combine([
                #Ex: 222 were admitted to hospitals
                ra.follows([
                    all_quantities, report_description
                ], 3) +
                ra.combine([
                    ra.follows([
                        ra.follows([my_search('to'), all_quantities]),
                        report_description
                    ], 2),
                    #Ex: bringing the infection death toll in the city to 15
                    ra.combine([
                        ra.follows([
                            report_description,
                            ra.follows([my_search('to'), all_quantities])
                        ], max_words_between=6)
                    ], prefer='match_length')
                ]) +
                #Ex: The average number of cases reported annually is 600
                ra.near([
                    ra.follows([
                        number_description,
                        report_description
                    ], 3),
                    ra.follows([my_search('VP'), all_quantities])
                ], 15),
                #Ex: it has already claimed about 455 lives in Guinea
                ra.follows([
                    ('death', my_search('CLAIM')),
                    people_quantity
                ], 2),
                #Ex: 1200 children between the ages of 2 and 5 are afflicted
                ra.near([
                    people_quantity,
                    ('case', my_search('AFFLICT'))
                ], 10),
                #Ex: Deaths: 13
                ra.follows([
                    ra.label('death', my_search('DEATHS :?')),
                    quantities
                ])
            ], prefer='match_length')
        )
        case_and_patient_info = ra.combine([
            age_description,
            patient_sex,
            case_count,
            ra.near([
                age_description,
                patient_sex,
                case_count,
            ], 3)
        ], prefer='match_length')
        keypoint_matches = ra.combine(
            keyword_attributes +
            [case_and_patient_info] +
            # In this invocation of near, keyword attributes can be paired with
            # eachother, but case_and_patient_info can only be paired with
            # keyword attributes.
            [ra.near(
                keyword_attributes + 
                [case_and_patient_info],
                6
            )],
            prefer='match_length'
        )
        doc.tiers['patientInfo'] = AnnoTier([
            KeypointSpan(kp_match, doc)
            for kp_match in keypoint_matches
        ])
        doc.tiers['patientInfo'].sort_spans()
        return doc
