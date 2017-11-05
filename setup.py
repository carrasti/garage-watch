"""A simple security camera management for my garage

setup.py base on https://github.com/pypa/sampleproject/blob/master/setup.py
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='garage-watch',
    version='0.1.0',

    description='Simple security camera management for my garage',
    long_description=long_description,

    url='https://github.com/carrasti/garage-watch',

    author='Carlos Arrastia',
    author_email='carlos.arrastia@gmail.com',

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Other Audience',
        'Topic :: Home Automation',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
    ],

    keywords='door sensor security camera garage',

    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'examples']),

    install_requires=['transitions'],
)