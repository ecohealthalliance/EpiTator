#!/usr/bin/env python
"""
Annotates noun chunks with:
- 'attribute' metadata for:
    infection, death, hospitalization, person
- 'count' metadata

Only includes spans which meet the criteria:
- Seem like they talk about a hospitalization, infection, or death
- Seem like they indicate a definite count of a number or refer to an
  individual (i.e. count: 1)

InfectionAnnotator errs on the side of excluding events. Internally, within
its annotate method, it calls functions which are defined below. Each function
contains code to extract a specific syntactic pattern, by looking for certain
combinations of lemmas, parts of speech, etc. in spaCy properties. This design
is due to the complexity of each of those individual patterns. By separating
them into distinct function calls, it is easier to isolate errors, and to know
where to add functionality. If a new syntactic pattern is to be added, you
should add a new function, then add it to the set of functions that
InfectionAnnotator calls in the annotate() method.

In general, these inner functions all return metadata dicts, and rely on
epitator.utils.merge_dicts() to merge them before generating AnnoSpans.
"""
from itertools import groupby
from operator import itemgetter

from .annospan import AnnoSpan
from .annotier import AnnoTier
from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator, TokenSpan
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


def generate_attributes(tokens, attribute_lemmas=attribute_lemmas):
    """
    Given a list of spaCy tokens and a dict of lemma attributes, return an
    AnnoSpan metadata dict with the appropriate attributes object.

    The attribute_lemmas dict should contain keys in the following form:
    {
        "pos_": {
            "attribute_tag": ["lemmas", "to", "match"]
        }
    }

    Multiple attribute tags may be supplied for a given part of speech.
    Possessive nouns are excluded, because they cause problems with
    assumptions elsewhere. This isn't the most elegant solution. A more
    elegant solution might, say, provide a set of conditions (e.g. noun, not
    possessive) and a set of indicator lemmas.
    """
    metadata = {}
    attributes = []
    if not hasattr(tokens, "__iter__"):
        tokens = [tokens]
    for t in tokens:
        if t.pos_ == "NOUN" and t.dep_ == "poss":
                continue
        for category, lemmas in attribute_lemmas.get(t.pos_, {}).items():
            if t.lemma_ in lemmas:
                attributes.append(category)

    metadata['attributes'] = attributes
    return(metadata)


def generate_counts(tokens, strict_only=False, debug=False):
    """
    Given a set of spaCy tokens, return an AnnoSpan metadata dict containing
    appropriate count metadata.

    strict_only -- Do not apply "lax count generation" (default False). Lax
    generation looks for numbers which are formatted with spaces as thousands
    separators, by allowing counts to be found in successive tokens with the
    cardinal/quantity properties *or* NUMMOD part of speech, rather than
    requiring that both be present. To avoid interpreting years as counts,
    there must be two successive tokens with these properties. If this causes
    lots of false positive matches, we should disable it.

    debug -- Include a debug_attributes key in the returned dictionary,
    flagging when certain potentially problematic techniques (including the
    above "lax" mode) have been used.

    Note: Some parts of this function assume that the token passed in is a
    noun chunk. Specifically, if no numeric counts can be found, we look for a
    singular in the first token, and if it is found, assign a count of 1.
    """
    metadata = {}
    if len(tokens) == 0:
        return metadata
    metadata["attributes"] = []
    debug_attributes = []
    quant_idx = [i for (i, t) in enumerate(tokens) if t.ent_type_ in ['CARDINAL', 'QUANTITY'] and t.dep_ == 'nummod']
    if len(quant_idx) == 1:
        count_text = tokens[quant_idx[0]].text
        metadata["count"] = parse_count_text(count_text)

    elif len(quant_idx) > 1:
        # If we find multiple tokens, we deal with them thus: First, we group
        # group consecutive tokens together in sub-lists: [1, 4, 5, 6, 8, 9]
        # becomes [[1], [4, 5, 6], [8, 9]]. If there is only one of these
        # groups, we process it as a single number. If there are multiple
        # groups, we add them all to metadata["count"] as a list. This will
        # cause InfectionAnnotator() to throw an error, however.
        groups = []
        for k, g in groupby(enumerate(quant_idx), lambda ix: ix[0] - ix[1]):
            groups.append(list(map(itemgetter(1), list(g))))
        if len(groups) == 1:
            count_text = " ".join([tokens[i].text for i in groups[0]])
            metadata["count"] = parse_count_text(count_text)
            debug_attributes.append("joined consecutive tokens")

    if "count" not in metadata.keys() and tokens[0].dep_ == "det":
        # If we haven't already extracted a count, and there is an article in
        # the noun chunk, we check to see if the chunk is plural. To do that,
        # we look at all the tokens, and if a token is a noun (e.g. "patients")
        # we check to see if the lower case version of it is the lemma (i.e.
        # canonical singular) version of it. If none of the tokens are plural,
        # we assume the noun phrase is singular and add a "1" to the count
        # metadata. Otherwise, we assume that it must be a phrase like "some
        # patients" and do nothing.
        token_is_not_lemma = [token.lower_ != token.lemma_ for token in tokens]
        token_is_noun = [token.pos_ == 'NOUN' for token in tokens]
        token_is_plural = ([l and n for l, n in zip(token_is_not_lemma, token_is_noun)])

        # So we don't match "In any case" or other similar things.
        exclude_articles = ["any"]
        exclude = tokens[0].lower_ in exclude_articles

        if not any(token_is_plural) and not exclude:
            metadata["count"] = 1
            debug_attributes.append("count_inferred_from_singular_nc")

    if "count" not in metadata.keys() and strict_only is False:
        # "Lax metadata generation" -- so-called because it looks for tokens
        # which are cardinal / quantity OR nummod.  This is meant to mostly
        # cope with things in ProMED that are formatted like "193 533", which
        # often trip up spaCy. If it finds a single token matching these
        # criteria, it does nothing, because these are likely to be years or
        # other single-token things, and this would increase the false positive
        # rate. It handles multiple tokens in the same manner as above.
        try:
            lax_quant_idx = [i for (i, t) in enumerate(tokens) if t.ent_type_ in ['CARDINAL', 'QUANTITY'] or t.dep_ == 'nummod']
            if len(lax_quant_idx) == 1:
                count_text = tokens[lax_quant_idx[0]].text
                metadata["count"] = parse_count_text(count_text)
                debug_attributes.append("LAX")
            elif len(lax_quant_idx) > 1:
                # warning("Using lax metadata generation.")
                # This loop groups consecutive indices into sub-lists.
                groups = []
                for k, g in groupby(enumerate(lax_quant_idx), lambda ix: ix[0] - ix[1]):
                    groups.append(list(map(itemgetter(1), list(g))))
                if len(groups) == 1:
                    count_text = "".join([tokens[i].text for i in groups[0]])
                    metadata["count"] = parse_count_text(count_text)
                    debug_attributes.extend(["joined consecutive tokens", "lax count identification"])
        except ValueError:
            metadata = {}
    if debug:
        metadata["debug_attributes"] = debug_attributes
    return(metadata)


def has_trigger_lemmas(metadata,
                       lemmas=["infection", "death", "hospitalization"]):
    """
    Return True if any lemmas in the metadata dict match lemmas of interest.

    By default, lemmas of interest are "infection", "death", and "hospitalization".

    Written to improve readability, since this is used a lot in the annotation functions.
    """
    return any([lemma in metadata["attributes"] for lemma in lemmas])


def has_single_count(metadata):
    """
    Return True if the metadata dictionary has a single value for a "count" key.

    Written to improve readability, since this is used a lot in the annotation functions.
    """
    return metadata.get("count") is not None and not isinstance(metadata["count"], list)


def from_noun_chunks_with_infection_lemmas(doc, debug=False):
    """
    Given an AnnoDoc, return a list of AnnoSpans which contain spaCy noun
    chunks and infection lemmas. Counts are also extracted and included in the
    metadata dicts.

    debug -- Include a "debug_attributes" list in AnnoSpan metadata
    dictioanries, containing strings corresponding to certain parts of code in
    this and other functions, to facilitate debugging.
    """
    nc_tier, tokens_tier = doc.require_tiers('spacy.noun_chunks', 'spacy.tokens', via=SpacyAnnotator)

    infection_spans = []

    for nc in nc_tier:
        # First, we check for trigger attributes in the noun chunks.
        debug_attributes = []
        nc_tokens = [t for t in tokens_tier.spans_contained_by_span(nc)]
        out_tokens = nc_tokens
        metadata = merge_dicts([
            generate_attributes(out_tokens),
            generate_counts(out_tokens, strict_only=False)
        ], unique=True)
        if has_trigger_lemmas(metadata):
            debug_attributes.append("attributes from noun chunk")

        # If the noun chunk is the subject of the root verb, we check the
        # ancestors for metadata lemmas too.
            if any(dep in [t.dep_ for t in nc_tokens] for dep in ["nsubj", "nsubjpass", "dobj"]):
                ancestors = [TokenSpan(a, doc, nc.offset) for a in nc.span.root.ancestors]
                ancestor_metadata = merge_dicts([
                    generate_attributes(ancestors),
                    generate_counts(ancestors)
                ], unique=True)
                # TODO: Maybe this should include "or has_counts(ancestor_metadata)"
                if has_trigger_lemmas(ancestor_metadata):
                    out_tokens.extend(ancestors)
                    metadata = merge_dicts([metadata, ancestor_metadata],
                                           unique=True)
                    debug_attributes.append("attributes from ancestors")

        if debug:
            metadata["debug_attributes"] = debug_attributes

        if has_trigger_lemmas(metadata) and has_single_count(metadata):
            start = min([t.start for t in out_tokens])
            end = max([t.end for t in out_tokens])
            infection_spans.append(AnnoSpan(start, end, doc, metadata=metadata))

    return(infection_spans)


def collapse_span_group(span_group):
    if len(span_group.base_spans) == 0:
        # Not a span group
        return span_group
    all_metadata = [
        {"attributes": [span_group.label]} if span_group.label else None,
        span_group.metadata if span_group.metadata else None,
    ] + [collapse_span_group(span).metadata for span in span_group.base_spans]
    all_metadata = [x for x in all_metadata if x is not None]
    all_metadata = merge_dicts(all_metadata)
    return AnnoSpan(span_group.start, span_group.end, span_group.doc, metadata=all_metadata)


def add_count_modifiers(spans, doc):
    spacy_tokens, spacy_nes = doc.require_tiers('spacy.tokens', 'spacy.nes', via=SpacyAnnotator)
    span_tier = AnnoTier(spans)
    spacy_lemmas = [span.token.lemma_ for span in spacy_tokens]

    def search_lemmas(lemmas, match_name=None):
        match_spans = []
        lemmas = set(lemmas)
        for span, lemma in zip(spacy_tokens, spacy_lemmas):
            if lemma in lemmas:
                match_spans.append(span)
        return AnnoTier(match_spans, presorted=True).label_spans(match_name)

    case_statuses = (
        search_lemmas(['suspect'], 'suspected') +
        search_lemmas(['confirm'], 'confirmed'))
    span_tier += span_tier.with_nearby_spans_from(case_statuses, max_dist=1)

    person_and_place_nes = spacy_nes.with_label('GPE') + spacy_nes.with_label('PERSON')
    modifier_lemma_groups = [
        'average|mean',
        'annual|annually',
        'monthly',
        'weekly',
        'cumulative|total|already',
        'incremental|new|additional|recent',
        'max|less|below|under|most|maximum|up',
        'min|greater|above|over|least|minimum|down|exceeds',
        'approximate|about|near|around',
        'ongoing|active'
    ]
    for group in modifier_lemma_groups:
        lemmas = group.split('|')
        results = search_lemmas(lemmas, match_name=lemmas[0])
        # prevent components of NEs like the "New" in New York from being
        # treated as count descriptors.
        results = results.without_overlaps(person_and_place_nes)
        span_tier += span_tier.with_nearby_spans_from(results)
    span_tier = span_tier.optimal_span_set(prefer="num_spans_and_no_linebreaks")
    return AnnoTier([collapse_span_group(span) for span in span_tier], presorted=True)


def from_noun_chunks_with_person_lemmas(doc, debug=False):
    """
    Given an AnnoDoc, return a list of AnnoSpans which contain spaCy noun
    chunks and person lemmas. Counts are also extracted and included in the
    metadata dicts.

    Not all person lemmas are returned. The annotator looks for infection lemmas in ancestors of person lemma tokens, to see if those people were infected, hospitalized, etc.

    debug -- Include a "debug_attributes" list in AnnoSpan metadata
    dictioanries, containing strings corresponding to certain parts of code in
    this and other functions, to facilitate debugging.
    """
    nc_tier, tokens_tier = doc.require_tiers('spacy.noun_chunks', 'spacy.tokens', via=SpacyAnnotator)

    infection_spans = []

    for nc in nc_tier:
        debug_attributes = []
        nc_tokens = [t for t in tokens_tier.spans_contained_by_span(nc)]
        metadata = merge_dicts([
            generate_attributes(nc_tokens),
            generate_counts(nc_tokens, strict_only=False)
        ], unique=True)
        # If the noun chunk's metadata indicates that it refers to a person,
        # we check the disjoint subtree.
        if "person" in metadata["attributes"]:
            out_tokens = nc_tokens
            debug_attributes.append("attributes from noun chunk")
            if any(dep in [t.dep_ for t in nc_tokens] for dep in ["nsubj", "nsubjpass", "dobj"]):
                ancestors = [TokenSpan(a, doc, nc.offset) for a in nc.span.root.ancestors]
                ancestor_metadata = merge_dicts([
                    generate_attributes(ancestors),
                    generate_counts(ancestors)
                ], unique=True)
                # Maybe this should include "or has_counts(ancestor_metadata)"
                if has_trigger_lemmas(ancestor_metadata):
                    out_tokens.extend(ancestors)
                    metadata = merge_dicts([metadata, ancestor_metadata],
                                           unique=True)
                    debug_attributes.append("attributes from ancestors")
            # If we still don't have a trigger lemma, we'll check the disjoint
            # subtree for infection lemmas. This is less precise than checking
            # ancestors, because it can include more of the sentence.
            if not has_trigger_lemmas(metadata):
                disjoint_subtree = [TokenSpan(w, doc, nc.offset) for w in nc.span.subtree if w.i not in [w.i for w in nc.span]]
                subtree_metadata = merge_dicts([
                    generate_attributes(disjoint_subtree),
                    generate_counts(disjoint_subtree)
                ], unique=True)
                # Maybe this should include "or has_counts(subtree_metadata)"
                if has_trigger_lemmas(subtree_metadata):
                    out_tokens.extend(disjoint_subtree)
                    metadata = merge_dicts([metadata, subtree_metadata],
                                           unique=True)
                    debug_attributes.append("attributes from disjoint subtree")

        if debug:
            metadata["debug_attributes"] = debug_attributes

        if ("person" in metadata["attributes"] and
                has_trigger_lemmas(metadata) and
                has_single_count(metadata)):
            start = min([t.start for t in out_tokens])
            end = max([t.end for t in out_tokens])
            infection_spans.append(AnnoSpan(start, end, doc, metadata=metadata))

    return(infection_spans)


class InfectionAnnotator(Annotator):
    def annotate(self, doc, debug=False):
        doc.require_tiers('spacy.tokens', 'spacy.nes', via=SpacyAnnotator)
        spans = []
        spans.extend(from_noun_chunks_with_infection_lemmas(doc, debug))
        spans.extend(from_noun_chunks_with_person_lemmas(doc, debug))
        tier = add_count_modifiers(spans, doc)
        return {'infections': tier}
