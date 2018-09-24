#!/usr/bin/env python3
"""
Setup for the package
"""

from setuptools import setup, find_packages


setup(
    name="cidc_cli",
    version='0.1.0',
    packages=find_packages(exclude=('.tests', 'Pipfile', 'Pipfile.lock')),
    entry_points={
        'console_scripts': [
            'cidc_cli = cli.interface.cli:main'
        ]
    },
    python_requires='>=3.6'
)
