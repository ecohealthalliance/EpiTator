#!/usr/bin/env python
"""An annie loader creates an AnnoDoc from a source such as a file or database.
The loader should perform as much annotation as is necessary to preserve parts
of document structure that would otherwise be lost. For example, if there is a
document header, it might be parsed and metadata stored in the AnnoDoc.properties.
If HTML tags are removed, certain tags might be transferred to an AnnoTier.
"""

import yaml
import BeautifulSoup

from annotator import AnnoDoc
from html_tag_annotator import HTMLTagAnnotator


class Loader():
    def load():
        """Create an AnnoDoc from a data source"""
        raise NotImplementedError("load method must be implemented in child")

class HealthMapFileLoader(Loader):
    """Loader for HealthMap data file in the ".md" format"""

    def load(self, filename):
        """Create an AnnoDoc from a HealthMap .md file. Parse the YAML header
        and put data into properties.
        """

        with open(filename, 'r') as f:
            raw = f.read()

        first_separator_start = raw.find("---\n", 0)
        second_separator_start = raw.find("\n---\n", 1)

        if first_separator_start is not 0 or second_separator_start is -1:
            raise Exception("Couldn't parse header from file", filename)

        header = raw[4:second_separator_start]
        header_data = yaml.load(header)
        raw_text = raw[second_separator_start + 5:]

        doc = AnnoDoc(raw_text)
        html_tag_annotator = HTMLTagAnnotator([])
        doc.add_tier(html_tag_annotator)
        doc.properties = header_data

        return doc
