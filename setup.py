import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open(os.path.join(os.path.dirname(__file__), 'epitator', 'version.py')) as f:
    exec(f.read())

setup(
    name='EpiTator',
    version=__version__,
    packages=['epitator', ],
    install_requires=['lazy', 'geopy', 'unicodecsv', 'spacy', 'numpy',
        'rdflib', 'python-dateutil', 'requests', 'six'],
)
