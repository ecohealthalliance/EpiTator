from .annotator import Annotator
from .spacy_annotator import SpacyAnnotator
from .metaspan import MetaSpan, MetaGroup
from .lemma_matcher import LemmaMatcher
from .count_identifier import CountIdentifier
from .annotier import AnnoTier


class InfectionAnnotator(Annotator):
    def annotate(self, doc):
        if "spacy.noun_chunks" not in doc.tiers:
            doc.add_tiers(SpacyAnnotator())
        nc_tier = doc.tiers["spacy.noun_chunks"]
        spans = []
        for nc in nc_tier:
            metaspan = MetaSpan(nc)
            metaspan.update_metadata(LemmaMatcher())
            metaspan.update_metadata(CountIdentifier())

            metaspan = MetaSpan(nc)
            metaspan.update_metadata(LemmaMatcher())
            metaspan.update_metadata(CountIdentifier())
            if "person" in metaspan.metadata["attributes"]:
                metaspan = MetaGroup([metaspan])
                disjoint_subtree = [w for w in nc.span.subtree if w.i not in [w.i for w in nc.span]]
                ancestors = [a for a in nc.span.root.ancestors]
                for words in [disjoint_subtree, ancestors]:
                    if len(words) == 0:
                        continue
                    span = MetaSpan(start=min([w.idx for w in words]),
                                    end=max([w.idx + len(w) for w in words]),
                                    doc=nc.doc)
                    span.update_metadata(LemmaMatcher())
                    span.update_metadata(CountIdentifier())
                    if any([attr in span.metadata["attributes"] for attr in ["infection", "death", "hospitalization"]]):
                        metaspan.append(span)
            if any([attr in metaspan.metadata["attributes"] for attr in ["infection", "death", "hospitalization"]]):
                spans.append(metaspan)
        return {'infections': AnnoTier(spans, presorted=True)}
