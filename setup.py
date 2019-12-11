#!/usr/bin/env python3
"""
Setup for the package
"""

from setuptools import setup, find_packages

from cli import __version__

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="cidc_cli",
    version=__version__,
    packages=find_packages(exclude=("tests")),
    entry_points={"console_scripts": ["cidc = cli.cli:cidc"]},
    description="A command-line interface for interacting with the CIDC.",
    # TODO: Add a long_description, since external people may use this.
    install_requires=requirements,
    python_requires=">=3.6",
)
