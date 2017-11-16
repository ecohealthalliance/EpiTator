import os
import io
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

root = os.path.dirname(__file__)
with open(os.path.join(root, 'epitator', 'version.py')) as f:
    exec(f.read())

with io.open(os.path.join(root, 'README.rst'), encoding='utf8') as f:
    readme = f.read()

setup(
    name='EpiTator',
    version=__version__,
    packages=['epitator', 'epitator.importers',],
    description = 'Annotators for extracting epidemiological information from text.',
    long_description=readme,
    author = 'EcoHealth Alliance',
    author_email = 'breit@ecohealthalliance.org',
    url = 'https://github.com/ecohealthalliance/EpiTator',
    keywords = 'nlp information extraction case counts death counts '
        'count extraction date extraction epidemiology '
        'keyword resolution toponym resolution '
        'disease resolution species resolution '
        'geoannotation geoname resolution',
    install_requires=[
        'geopy>=1.11.0',
        'unicodecsv>=0.14.1',
        'spacy==2.0.2',
        'numpy>=1.13.0',
        'rdflib>=4.2.2',
        'python-dateutil>=2.6.0',
        'requests>=2.13.0',
        'lazy',
        'six'],
    classifiers=['Topic :: Text Processing',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Text Processing :: Linguistic',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: Apache Software License']
)