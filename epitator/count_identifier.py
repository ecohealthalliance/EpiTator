from logging import warning
from .metagen import MetaGen
from .utils import parse_count_text


class CountIdentifier(MetaGen):
    def generate(self, span):
        words = span.tokens
        metadata = {}
        quant_idx = [i for (i, w) in enumerate(words) if w.ent_type_ in ['CARDINAL', 'QUANTITY'] and w.dep_ == 'nummod']
        if len(quant_idx) == 0:
            return {}
        elif len(quant_idx) > 1:
            # TODO: Handle this!
            warning("Multiple separate counts may exist, and the result may be incorrect.")
        count_text = words[quant_idx[0]].text
        metadata["count"] = parse_count_text(count_text)
        metadata["attributes"] = ["count"]
        return(metadata)
