#!/usr/bin/env python
"""Token Annotator"""

from annotator import *

import re

class GeonameHumanTagAnnotator:

    def __init__(self):
        pass

    # Must be called on a raw text string
    # TODO this affects the AnnoDoc's text, how to update it?
    def annotate_doc(self, doc):
        for sentence in doc.sentences:
            self.annotate_sentence(sentence)

    def annotate_sentence(self, sentence):

        # Need to run this first before other annotators because it strips tags
        # and transforms the text

        nongeotag_patt = re.compile('(<(?!(geo id="|/geo>))[^>]*>)')
        nobreaks_patt = re.compile('[\n\r\t]')
        tagless_text = nobreaks_patt.sub('',
            nongeotag_patt.sub('', sentence.text).strip())

        tag_patt = re.compile('(<[^>]*>)')
        chunks = tag_patt.split(tagless_text)

        retained_chunks = []
        geoname_chunks = []

        geoname_id = None
        for chunk in chunks:
            if chunk[0:9] == '<geo id="':
                geoname_id = chunk[9:-2]
            elif chunk and not (chunk[0] == '<' and chunk[-1] == '>'):
                retained_chunks.append(chunk)
                geoname_chunks.append(geoname_id)
                geoname_id = None
            else:
                pass # burning a tag

        sentence.text = ''.join(retained_chunks)

        spans = []

        index = 0
        for chunk, geoname_id in zip(retained_chunks, geoname_chunks):
            if geoname_id:
                spans.append(AnnoSpan(index, 
                                      index + len(chunk),
                                      sentence,
                                      label=geoname_id))
            index += len(chunk)

        sentence.tiers['gold_geonames'] = AnnoTier(spans)
                
        return sentence



