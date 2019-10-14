# -*- coding: utf-8 -*-

import setuptools

import id_sync

with open("requirements.txt") as fp:
    requirements = fp.read().splitlines()

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="id-sync",
    version=id_sync.__version__,
    author="Daniel Tröder",
    author_email="troeder@univention.de",
    description="ID Sync",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://www.univention.de/",
    install_requires=requirements,
    packages=setuptools.find_packages(),
    scripts=["queue_management", "schedule_user"],
    license="GNU Affero General Public License v3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
