#!/usr/bin/env python
# coding=utf8
import sys
import unittest

sys.path = ['./', './tests/annotator'] + sys.path

import test_utils
from annotator.annotator import AnnoDoc
from annotator.patient_info_annotator import PatientInfoAnnotator

class PatientInfoAnnotatorTest(unittest.TestCase):

    def setUp(self):
        self.annotator = PatientInfoAnnotator()

    def test_date_and_location_keywords(self):
        from annotator.jvm_nlp_annotator import JVMNLPAnnotator
        from annotator.geoname_annotator import GeonameAnnotator
        doc = AnnoDoc("""
        This year [2014], from January through July,
        there were 52 documented cases of rabies found in animals across Wyoming,
        48 of which were found in skunks. In the 3 years prior,
        there were only 27 cases where skunks tested positive.
        Last week [week of 25 Aug 2014],
        the 1st case of south central skunk rabies was found in Natrona County,
        a county with no confirmed rabid animals since 2002.
        """)
        doc.add_tier(JVMNLPAnnotator(['times']))
        doc.add_tier(GeonameAnnotator())
        doc.add_tier(self.annotator, keyword_categories={
            'date' : [
                span for span in doc.tiers['times'].spans
            ],
            'location' : [
                span for span in doc.tiers['geonames'].spans
            ]
        })
        span_dicts = [
            span.to_dict()
            for span in doc.tiers['patientInfo'].spans
        ]
        test_utils.assertHasProps(span_dicts[0], {
            'date' : {
                'label' : '2014'
            }
        })
        test_utils.assertHasProps(span_dicts[1], {
            'date' : {
                'label': '2014'
            }
        })
        test_utils.assertHasProps(span_dicts[2], {
            'date' : {
                'type' : 'DATE',
                # Currently, this is the label. TODO: Fix in time annotator?
                #'label': '2015-01',
            }
        })
        test_utils.assertHasProps(span_dicts[3], {
            'count' : {
                'number': 52
            },
            'location' : {
                'name' : 'Wyoming'
            },
            # There are a few problems with date ranges here.
            # 1. The date range info is not returned by our SUTime API AFAICT.
            # 2. It would be ideal to combine the start and end into one span.
            # Related: https://github.com/ecohealthalliance/jvm-nlp/issues/1
            'date' : {
                'label': '2014-07'
            }
        })
        test_utils.assertHasProps(span_dicts[4], {
            'date' : {
                'type': 'DURATION'
            },
            'count' : {
                'number' : 27
            }
        })
        test_utils.assertHasProps(span_dicts[5], {
            'date' : {
                'type': 'DATE',
                # Currently, this is the label. TODO: Fix in time annotator?
                #'label': '2014-W35',
            }
        })
        test_utils.assertHasProps(span_dicts[6], {
            'date' : {
                'type': 'DATE',
                # Currently, this is the label. TODO: Fix in time annotator?
                #'label': None,
            }
        })
        test_utils.assertHasProps(span_dicts[7], {
            'location' : {
                'name' : 'Natrona County'
            }
        })
        test_utils.assertHasProps(span_dicts[8], {
            'date' : {
                'label': '2002'
            }
        })

    def test_attribute_association(self):
        doc = AnnoDoc("""
        The first deaths reported were a seventy-two year old woman
        and a 6 month old infant.
        """)
        doc.add_tier(self.annotator)
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[0].metadata, {
            'age' : {
                'number': 72,
                'year_units': True
            },
            'female': True,
            'death' : True
        })
        test_utils.assertHasProps(doc.tiers['patientInfo'].spans[1].metadata, {
            'age' : {
                'number': 6,
                'month_units': True
            },
            'death' : True
        })
        self.assertEqual(test_utils.get_path(
            doc.tiers['patientInfo'].spans[1].metadata,
            'count.female'
        ), None)

    # TODO
    # case count not found in: "15 people hospitalized and ten people killed and 4 deaths and 11 cases"

if __name__ == '__main__':
    unittest.main()
