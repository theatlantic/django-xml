#!/usr/bin/env python
import re
import os.path
from setuptools import setup, find_packages


setup_kwargs = {}

try:
    setup_kwargs['long_description'] = open('README.rst').read()
except IOError:
    # Use the create_readme_rst command to convert README to reStructuredText
    pass

with open(os.path.join(os.path.dirname(__file__), "djxml", "__init__.py")) as f:
    for line in f:
        if m := re.search(r"""^__version__ = (['"])(.+?)\1$""", line):
            version = m.group(2)
            break
    else:
        raise LookupError("Unable to find __version__ in djxml/__init__.py")

setup(
    name='django-xml',
    version=version,
    install_requires=[
        'lxml',
        'pytz',
        'python-dateutil',
        'Django>=2.2',
    ],
    description="Provides an abstraction to lxml's XPath and XSLT " + \
                "functionality in a manner resembling django database models",
    author='The Atlantic',
    author_email='atmoprogrammers@theatlantic.com',
    url='https://github.com/theatlantic/django-xml',
    packages=find_packages(),
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'distutils.commands': [
            'create_readme_rst = djxml.build:create_readme_rst',
        ],
    },
    **setup_kwargs)
