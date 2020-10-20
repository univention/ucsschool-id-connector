# -*- coding: utf-8 -*-

# Copyright 2019-2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

from pathlib import Path

import setuptools

from ucsschool_id_connector.constants import APP_ID

with open("requirements.txt") as fp:
    requirements = fp.read().splitlines()

with open("README.rst", "r") as fh:
    long_description = fh.read()

with (Path(__file__).parent.parent / "VERSION.txt").open("r") as fp:
    version = fp.read().strip()

setuptools.setup(
    name=APP_ID,
    version=version,
    author="Daniel Tröder",
    author_email="troeder@univention.de",
    description="UCS@school ID Connector",
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
