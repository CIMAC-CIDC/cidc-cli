#!/usr/bin/env python3
"""
Setup for the package
"""

from setuptools import setup, find_packages


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="cidc_cli",
    version="0.1.0",
    packages=find_packages(exclude=(".tests", "Pipfile", "Pipfile.lock")),
    entry_points={
        "console_scripts": [
            "cidc_cli = cli.interface.cli:main",
            "cidc = cli2.cli:cidc",
        ]
    },
    install_requires=requirements,
    python_requires=">=3.6",
)
