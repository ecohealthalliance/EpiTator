from epitator.annodoc import AnnoDoc
from epitator.annospan import AnnoSpan, SpanGroup
from epitator.annotier import AnnoTier
from epitator.annotator import Annotator
from epitator.spacy_annotator import SpacyAnnotator, SentSpan, TokenSpan
from epitator.spacy_nlp import spacy_nlp
from epitator.utils import parse_spelled_number, flatten, merge_dicts
from lazy import lazy


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
        count = parse_spelled_number(count_text)
    if count == None:
        # print("Could not parse {}.".format(count_text))
        raise(ValueError)
    else:
        # print("Parsed {} as {}.".format(count_text, count)) if verbose == True else None
        return(count)


attribute_lemmas = {
    "NOUN": {
        # Patient is included under "infection" and "person"
        "infection": ["case", "victim", "infection", "instance", "diagnosis", "patient"],
        "death": ["death", "fatality"],
        "hospitalization": ["hospitalization"],
        # We include "people" because it doesn't lemmatize to "person" for some reason.
        "person": ["people", "person", "victim", "patient", "man", "woman", "male", "female", "employee"]
    },
    "ADJ": {
        "infection": ["infected", "sickened"],
        "death": ["dead", "deceased"],
        "hospitalization": ["hospitalized"]
    },
    # Stricken is in there because of spaCy not getting it as a past participle of "strike".
    "VERB": {
        "infection": ["infect", "sicken", "stricken", "strike", "diagnose"],
        "death": ["die"],
        "hospitalization": ["hospitalize", "admit"]
    }
}


def generate_metadata_for_words(words, attribute_lemmas = attribute_lemmas):
    """
    Given an iterable of text words, return a metadata object suitable for a
    CountSpan(). This is a dict optionally containing a list of "attributes"
    and an integer or double "count". The attributes returned are based on the
    dicts in the attribute_lemmas dict -- different for nouns, verbs, and
    adjectives.

    In addition, counts are handled separately, because we want to handle the
    case that a number is separated with either a comma or non-standard
    separator which might otherwise cause it to be interpreted as two separate
    numbers. This is not currently implemented!

    TODO: If we wanted to begin to swap in, say, a machine learning-trained
    classifier, I think that this is where we'd start — we could generate
    attributes based on some other thing which would output the results of the
    attribute generator in a format which EpiTator understands?
    """

    metadata = {}
    attributes = []
    
    # First we handle quantaties and cardinal numbers.
    # FIXME: It's probably silly to do this differently for counts, but I think
    # it's useful to use the index to determine whether we actually have two
    # separate numbers in the noun chunk.
    quant_idx = [i for (i, w) in enumerate(words) if w.ent_type_ in ['CARDINAL', 'QUANTITY'] and w.dep_ == 'nummod']

    if len(quant_idx) == 0:
        # print("No quantity tokens found.")
        pass
    elif len(quant_idx) > 1:
        # print("More than one quantity token found.")
        # TODO: Handle this!
        pass
    else:
        count_text = words[quant_idx[0]].text
        metadata["count"] = parse_count_text(count_text)
        attributes.append("count")

    # Second, we handle attributes assigned by  matching lemmas. Look at all
    # the words in the iterable for category lemmas. We use the words part of
    # speech to select the right lemmas dict.
    for i, w in enumerate(words):
        for category, lemmas in attribute_lemmas.get(w.pos_, {}).items(): # Clever girl
            if w.lemma_ in lemmas:
                attributes.append(category)
                # print("{} ({}) matches {} in category {}".format(w, w.pos_, w.lemma_, category))

    metadata['attributes'] = attributes
    return(metadata)


# TODO: This should really be an init() method for a CountSpan class.
def count_span_from_noun_chunk(nc):
    """
    Given a SentSpan containing a spaCy noun chunk, this will attempt to
    construct a CountSpan. We generate attributes for three things: the noun
    chunk, the remainder of the subtree, and its ancestors in the parse tree,
    based on the attribute lemmas dict.

    If the noun chunk contains a word related to infection, we include it and
    stop looking, because we assume that the noun chunk refers to a
    resultative of an infection event.

    If the noun chunk contains a lemma indicating a person, we continue
    looking for words in the subtree and ancestors which would indicate that
    this person was the victim of an infection event.

    Regardless, at the end of that process, we have a list of spaCy words and
    a list of attribute dicts. These are combined to generate the text span
    and a merged metadata object, which are used to create a CountSpan and
    returned.

    TODO: Have an argument flag for "compatibility mode", which would replace
    all attributes named "infection" with "case".

    If we continue down this path, I'd want to write a class which could take
    attribute-associated AnnoSpans -- say AttribSpans -- as arguments to event
    slots.
    """
    if not isinstance(nc, SentSpan):
        raise TypeError("Please give us a SentSpan.")

    # TODO: This should check that nc is actually a noun chunk. It should also
    # just expect a spaCy noun chunk. I could also see it being better to
    # accept stuff liberally here, so that it could take any AnnoSpan, check
    # if it's a noun chunk, and if so, get to work on it.
    nc_metadata = generate_metadata_for_words(nc.span)

    disjoint_subtree = [w for w in nc.span.subtree if w.i not in [w.i for w in nc.span]]
    subtree_metadata = generate_metadata_for_words(disjoint_subtree)

    ancestors = [a for a in nc.span.root.ancestors]
    ancestor_metadata = generate_metadata_for_words(ancestors)

    # Now we use some simple logic to assemble the final set of spans and
    # metadata for the span.
    if any([lemma in nc_metadata["attributes"] for lemma in ["infection", "death", "hospitalization"]]):
        spacy_words = [word for word in nc.span]
        metadata_dicts = [nc_metadata]
        sources = ["noun_chunk"]
    elif "person" in nc_metadata["attributes"]:
        spacy_words = [word for word in nc.span]
        metadata_dicts = [nc_metadata]
        sources = ["noun_chunk"]
        if any([lemma in subtree_metadata["attributes"] for lemma in ["infection", "death", "hospitalization"]]):
            # TODO: Consider iterating through until a triggering word is
            # found.
            spacy_words.extend(disjoint_subtree)
            metadata_dicts.append(subtree_metadata)
            sources.append("subtree")
        if any([lemma in ancestor_metadata["attributes"] for lemma in ["infection", "death", "hospitalization"]]):
            spacy_words.extend(ancestors)
            metadata_dicts.append(ancestor_metadata)
            sources.append("ancestors")
    else:
        return

    start = min([w.idx for w in spacy_words])
    end = max([w.idx + len(w) for w in spacy_words])
    anno_span = AnnoSpan(start, end, nc.span.doc)

    # FIXME: This is a little kludgy. But maybe it's as good as it can be.
    merged_metadata = merge_dicts(metadata_dicts, unique=["attributes"], simplify=["count"])
    # merged_metadata = defaultdict(list)
    # for d in metadata_dicts:
    #     for key, value in d.items():
    #         merged_metadata[key].append(value)
    # merged_metadata["attributes"] = flatten(merged_metadata["attributes"])
    # merged_metadata["count"] = flatten(merged_metadata["count"], simplify=True)
    # merged_metadata = dict(merged_metadata)
    # merged_metadata["sources"] = sources

    count_span = CountSpan(anno_span, merged_metadata)

    return count_span


class CountAnnotator2(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']
        noun_chunks = doc.tiers['spacy.noun_chunks']
        spacy_doc = spacy_tokens[0].token.doc

        count_spans = []
        for i, nc in enumerate(noun_chunks):
            count_spans.append(count_span_from_noun_chunk(nc))
        count_spans = [cs for cs in count_spans if cs is not None]
        return {'counts': AnnoTier(count_spans, presorted = True)}