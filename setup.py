#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from configparser import ConfigParser
from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()


def clean(k, v):
    rk = k[1:-1] if k[0] == '"' else k
    rv = v[1:-1] if v[0] == '"' else v
    return rk, rv


# Pipfile is in toml format and the only parser available in installation time
# is ConfigParser from the standar library. It can sort of parse it with some
# help.


pipfile = ConfigParser()
pipfile.read("Pipfile")
packages = dict(pipfile["packages"])

requirements = ["".join(clean(key, value)) for key, value in packages.items()]

setup_requirements = ["pytest-runner"]

test_requirements = ["pytest"]

setup(
    author="Nguyen Quang Huy",
    author_email="huy010579@gmail.com",
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
    ],
    description="A web application helper",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="stranal_app",
    name="stranal_app",
    packages=find_packages(include=["stranal_app"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/fadine/stranal_app",
    version="0.0.1",
    zip_safe=False,
)
