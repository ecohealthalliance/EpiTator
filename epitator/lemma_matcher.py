from .metagen import MetaGen


class LemmaMatcher(MetaGen):
    def __init__(self, lemma_dict=None):
        if lemma_dict is not None:
            self.attr_lemmas = lemma_dict
        else:
            self.attr_lemmas = {
                "NOUN": {
                    # Patient is included under "infection" and "person"
                    "infection": ["case", "victim", "infection", "instance", "diagnosis",
                                  "patient"],
                    "death": ["death", "fatality"],
                    "hospitalization": ["hospitalization"],
                    # We include "people" because it doesn't lemmatize to "person" for
                    # some reason.
                    "person": ["people", "person", "victim", "patient", "man", "woman",
                               "male", "female", "employee"]
                },
                "ADJ": {
                    "infection": ["infected", "sickened"],
                    "death": ["dead", "deceased"],
                    "hospitalization": ["hospitalized"]
                },
                # Stricken is in there because of spaCy not getting it as a past
                # participle of "strike".
                "VERB": {
                    "infection": ["infect", "sicken", "stricken", "strike", "diagnose"],
                    "death": ["die"],
                    "hospitalization": ["hospitalize", "admit"]
                }
            }

    def generate(self, span):
        words = span.tokens
        metadata = {}
        attributes = []
        for i, w in enumerate(words):
            for category, lemmas in self.attr_lemmas.get(w.pos_, {}).items():
                if w.lemma_ in lemmas:
                    attributes.append(category)

        metadata['attributes'] = attributes
        return(metadata)
