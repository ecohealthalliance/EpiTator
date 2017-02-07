try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='annie',
	version='0.3.1',
	packages=['annotator', ],
	install_requires=['lazy', 'nltk', 'pattern', 'numpy']
)
