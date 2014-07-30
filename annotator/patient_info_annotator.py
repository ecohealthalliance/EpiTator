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

    def annotate(self, doc):
        doc.setup_pattern()
        my_search = doc.p_search
        numbers = my_search('{CD+ and? CD? CD?}')
        number_ranges = ra.follows([
            ('range_start', numbers),
            my_search('-|to|and|or'),
            ('range_end', numbers)
        ], 2)
        min_number = ra.follows([
            my_search('ABOVE|OVER|LEAST|MINIMUM'),
            ('min', numbers)
        ], 1)
        max_number = ra.follows([
            my_search('LESS|BELOW|UNDER|MOST|MAXIMUM'),
            ('max', numbers)
        ], 1)
        quantities = ra.combine([
            number_ranges,
            min_number,
            max_number,
            ra.label('number', numbers)
        ])
        aprox_quantities = ra.near([
            ('aproximate', my_search('APROXIMATELY|ABOUT|NEAR|AROUND')),
            quantities
        ], 4)
        all_quantities = ra.combine([
            aprox_quantities, quantities
        ])
        time_quantities = ra.combine([
            ra.follows([
                all_quantities, ('year_units', my_search('YEAR'))
            ]),
            ra.follows([
                all_quantities, ('month_units', my_search('MONTH'))
            ])
        ])
        age_quantities = ra.near([
            time_quantities, my_search('AGE|OLD')
        ], 2)
        age_qualities = ra.combine([
            ra.label('child', my_search('CHILD')),
            ra.label('adult', my_search('ADULT')),
            ra.label('senior', my_search('ELDER|SENIOR')),
        ])
        age_description = ra.label('age', ra.combine([age_quantities,
            age_qualities
        ]))
        # Associate other features such as locations/times/occupations/symptoms
        patient_descriptions = ra.combine([
            age_description,
            ra.near([
                ('female', my_search("WOMAN|FEMALE|GIRL")), age_description
            ], 10),
            ra.near([
                ('male', my_search("MAN|MALE|BOY")), age_description
            ], 10)
        ], prefer='longer_match')

        def parse_dict(d):
            numeric_keys = ['number', 'min', 'max', 'range_start', 'range_end']
            for k, v in d.items():
                if isinstance(v, dict):
                    d[k] = parse_dict(v)
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
