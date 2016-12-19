try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='annie',
	version='0.2.2',
	packages=['annotator', ],
	install_requires=['lazy', 'nltk', 'pattern', ]
)
