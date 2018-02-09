#!/usr/bin/env python
"""
Annotates counts with the following attributes:
cumulative, case, death, age, hospitalization, approximate, min, max
"""
<<<<<<< HEAD
import re
from .annotator import Annotator, AnnoTier, AnnoSpan
from .annospan import SpanGroup
from .spacy_annotator import SpacyAnnotator, TokenSpan, SentSpan
from .date_annotator import DateAnnotator
from .spacy_nlp import spacy_nlp
from . import utils
import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

in_case_token = spacy_nlp(u"Break glass in case of emergency.")[3]

# I'll use the same definition of CountSpan as the base class. Keeping the definition here, though, so that this module is standalone.
class CountSpan(AnnoSpan):
    def __init__(self, span, metadata):
        self.start = span.start
        self.end = span.end
        self.doc = span.doc
        self.label = span.text
        self.metadata = metadata

    def to_dict(self):
        result = super(CountSpan, self).to_dict()
        result.update(self.metadata)
        result['text'] = self.text
        return result


def parse_count_text(count_text, verbose=False):
    try:
        count = int(count_text)
    except ValueError:
        pass # Try to parse it as a float
    try:
        count = float(count_text)
    except ValueError:
        pass # Try to parse it as a spelled number
        count = utils.parse_spelled_number(count_text)
    if count == None:
        print("Could not parse {}.".format(count_text))
        raise(ValueError)
    else:
        print("Parsed {} as {}.".format(count_text, count)) if verbose == True else None
        return(count)


class CountAnnotatorDepTree(Annotator):
    """
    This verison finds CARDINAL and QUANTITY entities, then looks for specific
    words near them in the parse tree, specifically as ancestors or children.
    """

    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']

        count_spans = []
        for token_span in spacy_tokens:
            token = token_span.token
            if token.ent_type_ in ['CARDINAL', 'QUANTITY'] and token.dep_ == "nummod":
                # TODO: Check that number doesn't overlap date or distance.
                # We should probably not use spaCy for this, because... hasn't it already
                # judged that these numbers don't overlap a date b/c they're QUANTITY.

                # Try to parse the text of the count value. This will probably not fail,
                # because it's already been identified by spaCy as a number, but just in case,
                # we'll prepare to skip it if it doesn't contain a number.
                try:
                    metadata = {'count': parse_count_text(token.text)}
                except ValueError:
                    print("Skipping {}.".format(token.text))
                    continue

                token_list = [token]
                attributes = []
                for ancestor in token.ancestors:
                    if ancestor.pos_ == "NOUN":
                        if ancestor.lemma_ in ["case", "infection", "patient"]:
                            token_list.append(ancestor)
                            attributes.append("case")
                        elif ancestor.lemma_ in ["death"]:
                            token_list.append(ancestor)
                            attributes.append("death")
                        elif ancestor.lemma_ in ["person", "people", "man", "woman", "child"]:
                            token_list.append(ancestor)
                    elif ancestor.pos_ == "VERB":
                        if ancestor.lemma_ in ["infect"]:
                            token_list.append(ancestor)
                            attributes.append("case")
                        if ancestor.dep_ in ["prep"]:
                            break # This is so we don't include the children that are actually a separate count

                # Add children so we can capture descriptions
                for child in token.children:
                    if child.lemma_ in ["additional", "more"]:
                        attributes.append("incremental")
                    elif child.lemma_ in ["total"]:
                        attributes.append("total")
                    token_list.append(child)

                # Create the final metadata dict.
                metadata['attributes'] = sorted(list(attributes))
                
                # Remove items from token_list with intervening punctuation; combine to form a SpanGroup
                # TODO: Make this a nice list comprehension.
                # TODO: I think there is inefficiency here, because we start out with TokenSpans and wind up with TokenSpans.
                # TODO: Move this above property inference, so that we don't get properties from removed spans.
                for i, item in enumerate(token_list):
                    spacy_span = token.doc[min(token.i, item.i):max(token.i, item.i)]
                    if any([t.text in ",.!?" for t in spacy_span]):
                        token_list.pop(i)
                count_span_group = SpanGroup([TokenSpan(t, doc) for t in token_list])

                # Right now we only add the count if it has a relevant attribute. This is
                # different from the behavior of the current count annotator, which
                # includes even non-case-counts so they can be suggested in EIDR Connect.
                if len(attributes) is not 0:
                    count_spans.append(CountSpan(count_span_group, metadata)) # This one includes verbs
        return {'counts_alt.dep_tree': AnnoTier(count_spans, presorted=True)}


class CountAnnotatorNounChunks(Annotator):
    """
    This verison iterates over spaCy noun chunks. If there is a CARDINAL or
    QUANTITY entity in that noun chunk, it checks other words in the noun chunk
    to see if they indicate that we might be dealing with a case.
    """

    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']

        # We get at the underlying spaCy doc using the tokens span, which is rather inelegant.
        spacy_doc = spacy_tokens[0].token.doc

        count_spans = []
        for noun_chunk in spacy_doc.noun_chunks:
            attributes = []
            # TODO: Parse the token which is a cardinal and/or quantity
            count_text = [t.text for t in noun_chunk if t.ent_type_ in ['CARDINAL', 'QUANTITY'] and t.dep_ == 'nummod']
            if len(count_text) == 0:
                continue
            else:
                # TODO: This needs to not do this if there is non-quantity text separating these tokens.
                metadata = {'count': parse_count_text("".join(count_text))}

            for t in noun_chunk:
                if t.pos_ == "NOUN":
                    if t.lemma_ in ["case", "infection", "patient"]:
                        attributes.append("case")
                    elif t.lemma_ in ["death"]:
                        attributes.append("death")
                    elif t.lemma_ in ["person", "people", "man", "woman", "child"]:
                        attributes.append("person")
                    elif noun_chunk.root.lemma_ in ["infect"]:
                        attributes.append("case")

                # TODO: Handle verbs for things like "additional", "incremental".
                # Will probably need to look at noun chunk's root's head's children.

                # Create the final metadata dict.
                metadata['attributes'] = sorted(list(attributes))
                
                # Remove items from token_list with intervening punctuation; combine to form a SpanGroup
                # TODO: Make this a nice list comprehension.
                # TODO: I think there is inefficiency here, because we start out with TokenSpans and wind up with TokenSpans.
                # TODO: Move this above property inference, so that we don't get properties from removed spans.
                

                count_span = SpanGroup([SentSpan(noun_chunk, doc)])

                # TODO Getting an error here. I think that one cannot create a 
                if len(attributes) is not 0:
                    count_spans.append(CountSpan(count_span, metadata)) # This one includes verbs
        return {'counts_alt.noun_chunks': AnnoTier(count_spans, presorted=True)}
