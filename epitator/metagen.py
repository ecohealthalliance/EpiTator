class MetaGen(object):
    def generate(self, span):
        """Take a MetaSpan and generate a dict of metadata."""
        raise NotImplementedError("generate method must be implemented in child")
