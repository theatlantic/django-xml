#!/usr/bin/env python
from setuptools import setup, find_packages


setup_kwargs = {}

try:
    setup_kwargs['long_description'] = open('README.rst').read()
except IOError:
    # Use the create_readme_rst command to convert README to reStructuredText
    pass


setup(
    name='django-xml',
    version="3.0.0",
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
