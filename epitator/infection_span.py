from .annodoc import AnnoDoc
from .annospan import AnnoSpan, SpanGroup
from .annotier import AnnoTier
from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator, SentSpan, TokenSpan
from .spacy_nlp import spacy_nlp
from .utils import parse_spelled_number, flatten, merge_dicts
from .infection_annotator import attribute_lemmas, parse_count_text


# Alternate version scratch

class InfectionSpan(AnnoSpan):
    def __init__(self, span, attribute_lemmas = attribute_lemmas):
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
        if not isinstance(span, SentSpan):
            raise TypeError("Please give us a SentSpan.")

        self.attribute_lemmas = attribute_lemmas

        # TODO: This should check that span is actually a noun chunk. It should also
        # just expect a spaCy noun chunk. I could also see it being better to
        # accept stuff liberally here, so that it could take any AnnoSpan, check
        # if it's a noun chunk, and if so, get to work on it.
        noun_chunk = span.span
        disjoint_subtree = [w for w in span.span.subtree if w.i not in [w.i for w in span.span]]
        ancestors = [a for a in span.span.root.ancestors]

        nc_metadata = self.generate_metadata_for_words(noun_chunk)
        subtree_metadata = self.generate_metadata_for_words(disjoint_subtree)
        ancestor_metadata = self.generate_metadata_for_words(ancestors)


        # Now we use some simple logic to assemble the final set of spans and
        # metadata for the span.
        spacy_words = [word for word in span.span]
        metadata_dicts = [nc_metadata]
        sources = ["noun_chunk"]
        if "person" in nc_metadata["attributes"]:
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

        start = min([w.idx for w in spacy_words])
        end = max([w.idx + len(w) for w in spacy_words])

        merged_metadata = merge_dicts(metadata_dicts, unique=["attributes"], simplify=["count"])

        # Checks for integrity.
        # - Is "count" at most one value?
        if "count" in merged_metadata.values() and isinstance(merged_metadata["count"], list):
            raise TypeError("Metadata includes multiple count values.")

        self.start = start
        self.end = end
        self.doc = span.doc
        self.label = self.text
        self.metadata = merged_metadata

    def to_dict(self):
        result = super(CountSpan, self).to_dict()
        result.update(self.metadata)
        result['text'] = self.text
        return result

    def generate_metadata_for_words(self, words):
        """
        Given an iterable of text words, returns a metadata object suitable for a
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
            pass
        elif len(quant_idx) > 1:
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
            for category, lemmas in self.attribute_lemmas.get(w.pos_, {}).items():
                if w.lemma_ in lemmas:
                    attributes.append(category)

        metadata['attributes'] = attributes
        return(metadata)


class InfectionSpanAnnotator(Annotator):
    def annotate(self, doc):
        if 'spacy.tokens' not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        spacy_tokens = doc.tiers['spacy.tokens']
        spacy_sentences = doc.tiers['spacy.sentences']
        spacy_nes = doc.tiers['spacy.nes']
        noun_chunks = doc.tiers['spacy.noun_chunks']

        metadata_spans = [InfectionSpan(nc) for nc in noun_chunks]
        infection_spans = [span for span in metadata_spans if "infection" in span.metadata["attributes"]]

        return {'infection_spans': AnnoTier(infection_spans, presorted = True)}
