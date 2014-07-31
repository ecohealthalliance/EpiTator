#!/usr/bin/env python
"""Annotator to add NLP annotations from REST calls to a webservice"""

import requests

from annotator import *


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

        data = {'text': doc.text}

        # Stanford SUTime can use a reference date to canonicalize relative
        # dates like "tomorrow." If we have a doc.date for this document,
        # send it along and the jvm-nlp will not attempt to find a reference
        # date in the beginning of the document.
        if doc.date:
            data['referenceDate'] = doc.date.strftime('%Y-%m-%d')

        request = requests.post(self.base_url + self.annotate_path, data)

        spans = []

        for tier in self.tiers:
            for request_span in request.json()['tiers'][tier]['spans']:

                span = AnnoSpan(request_span['start'],
                                request_span['stop'],
                                doc,
                                label=request_span['label'])
                span.type = request_span['type']
                spans.append(span)

            doc.tiers[tier] = AnnoTier(spans)

        return doc
