#!/usr/bin/env python3
"""
Setup for the package
"""

from setuptools import setup

setup(
    name="cidc-cli",
    version='0.1.0',
    packages=['interface', 'tests', 'upload', 'auth0'],
    entry_points={
        'console_scripts': [
            'cidc-cli = interface.cli:main'
        ]
    },
    python_requires='>=3'
)
