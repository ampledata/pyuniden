#!/usr/bin/env python
# -*- coding: utf-8 -*-


import setuptools


setuptools.setup(
    name='pyuniden',
    version='0.0.1',
    description='Uniden Scanner API',
    zip_safe=False,
    packages=['pyuniden'],
    setup_requires=['coverage==3.7.1', 'nose>=1.3.1'],
    install_requires=[
        'pyyaml',
        'pyserial'
    ]
)
