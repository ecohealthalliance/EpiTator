#!/usr/bin/env python
"""
Annotates noun chunks with:
- 'attribute' metadata for:
    infection, death, hospitalization, person
- 'count' metadata

TODO:
- list noun chunks with definite and indefinite articles as ['count': 1]
- implement 'attribute' metadata for:
    cumulative, age, approximate, min, max

These could be added in this annotator, but might be better suited elsewhere.
"""
from logging import warning
from itertools import groupby
from operator import itemgetter
from .annospan import AnnoSpan
from .annotier import AnnoTier
from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator
from .utils import merge_dicts
from .utils import parse_count_text


attribute_lemmas = {
    "NOUN": {
        # Patient is included under "infection" and "person"
        "infection": ["case", "victim", "infection", "instance", "diagnosis",
                      "patient"],
        "death": ["death", "fatality"],
        "hospitalization": ["hospitalization"],
        # We include "people" because it doesn't lemmatize to "person" for
        # some reason.
        "person": ["people", "person", "victim", "patient", "man", "woman",
                   "male", "female", "employee", "child"]
    },
    "ADJ": {
        "infection": ["infected", "sickened"],
        "death": ["dead", "deceased"],
        "hospitalization": ["hospitalized"]
    },
    # Stricken is in there because of spaCy not getting it as a past
    # participle of "strike".
    "VERB": {
        "infection": ["infect", "sicken", "stricken", "strike", "diagnose", "afflict"],
        "death": ["die"],
        "hospitalization": ["hospitalize", "admit"]
    }
}


def spacy_tokens_for_span(span):
    doc = span.doc
    if "spacy.tokens" not in doc.tiers:
        doc.add_tier(SpacyAnnotator())
    tokens_tier = span.doc.tiers["spacy.tokens"]
    tokens = [t.token for t in tokens_tier.spans_contained_by_span(span)]
    return(tokens)


def generate_attributes(tokens, attribute_lemmas=attribute_lemmas):
    metadata = {}
    attributes = []
    for i, t in enumerate(tokens):
        for category, lemmas in attribute_lemmas.get(t.pos_, {}).items():
            if t.lemma_ in lemmas:
                attributes.append(category)

    metadata['attributes'] = attributes
    return(metadata)


def generate_counts(tokens, strict=False):
    metadata = {}
    quant_idx = [i for (i, t) in enumerate(tokens) if t.ent_type_ in ['CARDINAL', 'QUANTITY'] and t.dep_ == 'nummod']
    if len(quant_idx) == 1:
        count_text = tokens[quant_idx[0]].text
        metadata["count"] = parse_count_text(count_text)
    elif len(quant_idx) > 1:
        # This loop groups consecutive indices into sub-lists.
        groups = []
        for k, g in groupby(enumerate(quant_idx), lambda ix: ix[0] - ix[1]):
            groups.append(list(map(itemgetter(1), list(g))))
        if len(groups) == 1:
            count_text = " ".join([tokens[i].text for i in groups[0]])
            metadata["count"] = parse_count_text(count_text)
            metadata["attributes"] = ["JOINED_CONSECUTIVE_TOKENS"]
        elif len(groups) > 1:
            # FIXME: This should operate on "groups"
            warning("Multiple separate counts may exist, and the result may be incorrect.")
            count_texts = [tokens[i].text for i in quant_idx]
            counts = []
            for t in count_texts:
                counts.append(parse_count_text(t))
            metadata["count"] = counts
            metadata["attributes"] = ["MULTIPLE_COUNT_WARNING"]
    elif len(quant_idx) == 0:
        if strict is True:
            return {}
        elif strict is False:
            warning("Using lax metadata generation.")
            metadata = generate_lax_counts(tokens)
    return(metadata)

# TODO: Fix this pattern
def generate_lax_counts(tokens):
    metadata = {}
    quant_idx = [i for (i, t) in enumerate(tokens) if t.ent_type_ in ['CARDINAL', 'QUANTITY'] or t.dep_ == 'nummod']
    if len(quant_idx) == 1:
        count_text = tokens[quant_idx[0]].text
        metadata["count"] = parse_count_text(count_text)
    elif len(quant_idx) > 1:
        # This loop groups consecutive indices into sub-lists.
        groups = []
        for k, g in groupby(enumerate(quant_idx), lambda ix: ix[0] - ix[1]):
            groups.append(list(map(itemgetter(1), list(g))))
        if len(groups) == 1:
            count_text = " ".join([tokens[i].text for i in groups[0]])
            metadata["count"] = parse_count_text(count_text)
            metadata["attributes"] = ["JOINED_CONSECUTIVE_TOKENS"]
        elif len(groups) > 1:
            # FIXME: This should operate on "groups"
            warning("Multiple separate counts may exist, and the result may be incorrect.")
            count_texts = [tokens[i].text for i in quant_idx]
            counts = []
            for t in count_texts:
                counts.append(parse_count_text(t))
            metadata["count"] = counts
            metadata["attributes"] = ["MULTIPLE_COUNT_WARNING"]
    elif len(quant_idx) == 0:
        return {}
    metadata["attributes"].append("LAX")
    return(metadata)


class InfectionSpan(AnnoSpan):
    def __init__(self, source_span):
        """
        Initialized by passing in an AnnoSpan, this class will return a new
        span based on that AnnoSpan, but with 'attributes' and 'count'
        metadata slots populated, if appropriate.

        If the noun chunk contains a word related to infection, we include it and
        stop looking, because we assume that the noun chunk refers to a
        resultative of an infection event.

        If the noun chunk contains a lemma indicating a person, we continue
        looking for words in the subtree and ancestors which would indicate that
        this person was the victim of an infection event.

        Regardless, at the end of that process, we have a list of spaCy words and
        a list of attribute dicts. These are combined to generate the text span
        and a merged metadata object, which are used to create a AnnoSpan and
        returned.

        TODO: Have an argument flag for "compatibility mode", which would replace
        all attributes named "infection" with "case".

        If we continue down this path, I'd want to write a class which could take
        attribute-associated AnnoSpans -- say AttribSpans -- as arguments to event
        slots.
        """
        doc = source_span.doc
        if "spacy.noun_chunks" not in doc.tiers:
            doc.add_tier(SpacyAnnotator())

        ncs = doc.tiers["spacy.noun_chunks"].spans_contained_by_span(source_span)
        if len(ncs) is 0:
            raise ValueError("Source span does not contain a noun chunk.")
        elif len(ncs) > 1:
            warning("Source span contains more than one noun chunk.")
            nugget = ncs[0]
        else:
            nugget = ncs[0]

        tokens = [token for token in nugget.span]
        metadata = merge_dicts([
            generate_attributes(tokens),
            generate_counts(tokens)
        ], unique=True)

        if any([lemma in metadata["attributes"]
               for lemma in ["infection", "death", "hospitalization"]]):
            sources = ["noun_chunk"]

        elif "person" in metadata["attributes"]:
            sources = ["noun_chunk"]

            disjoint_subtree = [w for w in nugget.span.subtree if w.i not in [w.i for w in nugget.span]]
            subtree_metadata = merge_dicts([
                generate_attributes(disjoint_subtree),
                generate_counts(disjoint_subtree)
            ], unique=True)
            ancestors = [a for a in nugget.span.root.ancestors]
            ancestor_metadata = merge_dicts([
                generate_attributes(ancestors),
                generate_counts(ancestors)
            ], unique=True)

            if any([lemma in subtree_metadata["attributes"]
                   for lemma in ["infection", "death", "hospitalization"]]):
                # TODO: Consider iterating through until a triggering word is
                # found.
                tokens.extend(disjoint_subtree)
                metadata = merge_dicts([
                    metadata,
                    subtree_metadata
                ], unique=True)
                sources.append("subtree")
            if any([lemma in ancestor_metadata["attributes"]
                   for lemma in ["infection", "death", "hospitalization"]]):
                tokens.extend(ancestors)
                metadata = merge_dicts([
                    metadata,
                    ancestor_metadata
                ], unique=True)
                sources.append("ancestors")

        if "count" not in metadata.keys() and tokens[0].dep_ == "det":
            metadata["count"] = 1

        # Is "count" at most one value?
        if "count" in metadata.values() and isinstance(metadata["count"], list):
            raise TypeError("Metadata includes multiple count values.")

        self.start = min([w.idx for w in tokens])
        self.end = max([w.idx + len(w) for w in tokens])
        self.doc = doc
        self.metadata = metadata
        self.label = self.text


class InfectionAnnotator(Annotator):
    def __init__(self, inclusion_filter=["infection", "death", "hospitalization"]):
        self.inclusion_filter = inclusion_filter

    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        noun_chunks = doc.tiers['spacy.noun_chunks']

        spans = []
        for i, nc in enumerate(noun_chunks):
            candidate_span = InfectionSpan(nc)
            if self.inclusion_filter is None:
                spans.append(candidate_span)
            elif any([attribute in candidate_span.metadata["attributes"]
                     for attribute in self.inclusion_filter]):
                spans.append(candidate_span)
        spans = [span for span in spans if len(span.metadata['attributes']) is not 0]

        return {'infections': AnnoTier(spans, presorted=True)}
