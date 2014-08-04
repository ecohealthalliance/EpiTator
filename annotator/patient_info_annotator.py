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
        to the patient descriptions under attributes corresponding to the their
        categories.
        """
        doc.setup_pattern()
        my_search = doc.p_search
        numbers = my_search('{CD+ and? CD? CD?}')
        number_ranges = ra.follows([
            ('range_start', numbers),
            my_search('-|to|and|or'),
            ('range_end', numbers)
        ], 2)
        min_number = ra.follows([
            my_search('GREATER|ABOVE|OVER|LEAST|MINIMUM|DOWN'),
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
        all_quantities = ra.combine([
            approx_quantities, quantities
        ])
        time_quantities = ra.combine([
            all_quantities,
            ra.follows([
                all_quantities, ('year_units', my_search('YEAR'))
            ]),
            ra.follows([
                all_quantities, ('month_units', my_search('MONTH'))
            ])
        ], prefer='longer_match')
        age_quantities = ra.near([
            time_quantities, my_search('AGE|OLD')
        ], 2)
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
                my_search('[' + '|'.join(kws) + ']')
            )
        patient_descriptions = ra.combine([
            age_description,
            patient_sex,
            ra.near([
                patient_sex,
                age_description,
                # I'm deliberately avoiding creating patient descriptions from
                # keywords that appear alone since I believe there will be a
                # high false positive rate.
                keyword_attributes
            ], 8)
        ], prefer='longer_match')

        def parse_dict(d):
            numeric_keys = ['number', 'min', 'max', 'range_start', 'range_end']
            for k, v in d.items():
                if isinstance(v, dict):
                    d[k] = parse_dict(v)
                elif k in keyword_categories.keys():
                    d[k] = utils.restrict_match(v).string
                elif k in numeric_keys:
                    # Check for None?
                    d[k] = utils.parse_spelled_number(
                        v.string.split('-')
                    )
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
                spans.append(span)
        
        doc.tiers['patientInfo'] = AnnoTier(spans)
        doc.tiers['patientInfo'].sort_spans()
        return doc
