# -*- coding: utf-8 -*-

# Copyright 2024 Univention GmbH
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


import random
import subprocess

import pytest
import requests
from univention.config_registry import ConfigRegistry
from univention.udm import UDM

ucr = ConfigRegistry()
ucr.load()


@pytest.fixture()
def ldap_base():
    return ucr["ldap/base"]


@pytest.fixture()
def udm():
    return UDM.admin().version(2)


@pytest.fixture()
def make_dn(ldap_base):
    def _make_dn(identifier, common_name):
        return f"{identifier},cn={common_name},{ldap_base}"

    return _make_dn


@pytest.fixture()
def hostname():
    with open("/etc/hostname", "r") as fp:
        hostname = fp.read()
    return hostname.strip()


@pytest.fixture()
def admin_token(hostname):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "",
        "username": "Administrator",
        "password": "univention",
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    response = requests.post(
        f"https://{hostname}/ucsschool-id-connector/api/token", headers=headers, data=data
    )
    return response.json()["access_token"]


@pytest.fixture()
def random_school_name():
    return f"pt{random.randint(0, 1000000)}"


@pytest.fixture()
def schedule_item():
    def _schedule_item(item_type, item_name):
        subprocess.check_output(
            ["univention-app", "shell", "ucsschool-id-connector", f"src/schedule_{item_type}", item_name]
        )

    return _schedule_item
