#!/usr/bin/env python
# -*- coding: utf-8 -*-


import setuptools


setuptools.setup(
    name='uniden_api',
    version=render_version(),
    description='Uniden Scanner API',
    zip_safe=False,
    packages=['uniden_api'],
    setup_requires=['coverage==3.7.1', 'nose>=1.3.1'],
    install_requires=[
        'pyyaml',
        'pyserial'
    ]
)
