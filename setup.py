# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

name = 'abstract_salad_bar'
description = (
    'A reimplementation of the abstract salad bar app.'
)
version = '0.0.0'


setup(
    name=name,
    version=version,
    description=description,
    author='Pieter',
    author_email='pietpiet@fastmail.net',
    packages=find_packages(),
    namespace_packages=name.split('.')[:-1],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'morepath'
    ],
    extras_require=dict(
        test=[
            'pytest',
            'webtest',
        ],
    ),
    entry_points=dict(
        console_scripts=[
            'run-app = abstract_salad_bar.__main__:run',
        ],
    ),
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Web Environment',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ]
)
