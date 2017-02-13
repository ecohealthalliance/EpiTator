import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open(os.path.join(os.path.dirname(__file__), 'annotator', 'version.py')) as f:
    exec(f.read())

setup(
    name='annie',
	version=__version__,
	packages=['annotator', ],
	install_requires=['lazy', 'nltk', 'pattern', 'numpy']
)

