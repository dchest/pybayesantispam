# -*- coding: UTF-8 -*-

import setuptools
from distutils.core import setup

setup(
    name='pybayesantispam',
    version='1.0',
    author='Dmitry Chestnykh',
    py_modules=['bayes'],
    url='https://github.com/dchest/pybayesantispam',
    license=open('LICENSE', 'r').read(),
    description='Simple Bayesian spam rating',
    long_description="""\
Simple Bayesian spam rating in Python that is easy to use, small, contained in
a single file, and doesn't require any external modules.
""",
)
