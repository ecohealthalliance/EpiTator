#!/usr/bin/env python
"""
Annotates patient descriptions.
"""
import re
from collections import defaultdict

from annotator import *
import result_aggregators as ra
import utils

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
        ], prefer='longer_match')

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
            keyword_attributes += ra.label(
                cat,
                my_search('[' + '|'.join(map(pattern.search.escape, kws)) + ']')
            )
        quantity_modifiers = (
            ra.label('average', my_search('AVERAGE|MEAN')) +
            ra.label('annual', my_search('ANNUAL|ANNUALLY')) +
            ra.label('monthly', my_search('MONTHLY')) +
            ra.label('weekly', my_search('WEEKLY')) +
            ra.label('cumulative', my_search('TOTAL|CUMULATIVE|ALREADY'))
        )
        all_quantities = ra.combine([
            ra.near([
                quantity_modifiers,
                maybe_approx_quantities
            ], 2),
            maybe_approx_quantities
        ], prefer='longer_match')
        person = my_search('PERSON|CHILD|ADULT|ELDER|PATIENT|LIFE')
        report_type = map(utils.restrict_match, (
            ra.label('death',
                my_search('DIED|DEATHS|FATALITIES|KILLED')
            ) +
            ra.label('hospitalization',
                my_search('HOSPITAL|HOSPITALIZED')
            ) +
            ra.label('case',
                my_search(
                    'CASE|INFECTION|INFECT'
                ) + person
            )
        ))
        report_description = ra.combine([
            report_type,
            ra.near([report_type, report_type], 2)
        ], prefer='longer_match')
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
                #Ex: The average number of cases reported annually is 600
                ra.near([
                    ra.follows([
                        number_description,
                        report_description
                    ], 3),
                    all_quantities
                ], 30),
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
            ], prefer='longer_match')
        )
        patient_descriptions = ra.combine([
            age_description,
            patient_sex,
            case_count,
            ra.near([
                patient_sex,
                age_description,
                # I'm deliberately avoiding creating patient descriptions from
                # keywords that appear alone since I believe there will be a
                # high false positive rate.
                keyword_attributes,
                case_count
            ], 3)
        ], prefer='longest_total')

        def parse_dict(d):
            numeric_keys = ['number', 'min', 'max', 'range_start', 'range_end']
            for k, v in d.items():
                if isinstance(v, dict):
                    d[k] = parse_dict(v)
                elif k in keyword_categories.keys():
                    d[k] = utils.restrict_match(v).string
                elif k in numeric_keys:
                    # Check for None?
                    d[k] = utils.parse_spelled_number(v.string)
                else:
                    d[k] = True
            return d

        spans = []
        for desc in patient_descriptions:
            metadata = parse_dict(desc.groupdict())
            metadata['text'] = desc.string

            offsets_tuples = utils.find_all_match_offsets(doc.text, desc)
            for offsets_tuple in offsets_tuples:
                span = AnnoSpan(
                    offsets_tuple['fullMatch'][0],
                    offsets_tuple['fullMatch'][1],
                    doc,
                    label=desc.string
                )
                span.metadata = metadata
                span.__match__ = desc
                spans.append(span)

        doc.tiers['patientInfo'] = AnnoTier(spans)
        doc.tiers['patientInfo'].sort_spans()
        return doc
