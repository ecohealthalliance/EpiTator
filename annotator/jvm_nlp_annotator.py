#!/usr/bin/env python
"""Annotator to add NLP annotations from REST calls to a webservice"""

import json
import dateutil.parser

import requests

from annotator import *
from time_expressions import *

class StanfordSpan(AnnoSpan):

    def __init__(self, span_dict, doc):
        self.start = span_dict['start']
        self.end = span_dict['stop']
        self.doc = doc
        self.span_dict = span_dict
        if 'label' in span_dict:
            self.label = span_dict['label']
        else:
            self.label = self.text
        if 'type' in span_dict:
            self.type = span_dict['type']

    def to_dict(self):
        result = super(StanfordSpan, self).to_dict()
        result.update(self.span_dict)
        del result['start']
        del result['stop']
        return result

class JVMNLPAnnotator():

    default_base_url = 'http://localhost:8080'
    annotate_path = '/annotate/getNLPAnnotations'

    def __init__(self, tiers, base_url=None):
        """Specify a list of tiers that we want to transfer from the service
        result to the AnnoDoc. Specify base_url if it differs from the default.
        """
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = self.default_base_url

        self.tiers = tiers

    def annotate(self, doc):
        """Annotate a document by taking the text and sending it to the
        anootation server.
        """

        # Stanford SUTime can use a reference date to canonicalize relative
        # dates like "tomorrow." If we have a doc.date for this document,
        # send it along and the jvm-nlp will not attempt to find a reference
        # date in the beginning of the document.
        # if doc.date:
        #     data['referenceDate'] = doc.date.strftime('%Y-%m-%d')
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        request = requests.post(self.base_url + self.annotate_path,
                                data=doc.to_json(),
                                headers=headers)

        # Why aren't we using a swagger-generated client here? Because they
        # don't have Maps very well, so the tiers maps doesn't work out.

        return_json = request.json()

        if doc.text != return_json['text']:
            raise Exception("text changed after being sent back from jvm-nlp")

        # If we don't have a date already and one comes back from the jvm-nlp,
        # make that the new doc.date
        if 'date' in return_json:
            return_date = dateutil.parser.parse(return_json['date'][:-1])
            if doc.date:
                if doc.date != return_date:
                    raise Exception("doc.date changed after jvm-nlp, was %s is now %s"
                                    % (doc.date, return_date))
            else:
                doc.date = return_date

        for tier in self.tiers:

            spans = []

            for request_span in return_json['tiers'][tier]['spans']:
                span = StanfordSpan(request_span, doc)
                if 'timePoint' in request_span:
                    span.timePoint = TimePoint.from_json(request_span['timePoint'])
                if 'timeRange' in request_span:
                    span.timeRange = TimeRange.from_json(request_span['timeRange'])
                if 'timeDuration' in request_span:
                    span.timeDuration = TimeDuration.from_json(request_span['timeDuration'])
                if 'timeSet' in request_span:
                    span.timeSet = TimeSet.from_json(request_span['timeSet'])

                spans.append(span)

            doc.tiers[tier] = AnnoTier(spans)

        return doc
