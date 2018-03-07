#!/usr/bin/env python3
"""
Setup for the package
"""

from setuptools import setup

setup(
    name="CIDC-CLI",
    version='0.1.0',
    packages=['interface', 'tests', 'upload'],
    entry_points={
        'console_scripts': [
            'CIDC-CLI = interface.cli:main'
        ]
    },
    python_requires='>=3'
)
