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

import json

import requests

LOG_DIR = "/var/log/univention/ucsschool-id-connector"


def faulty_request_response(response: requests.models.Response, expected_code: int) -> str:
    return (
        f"Got faulty response! Expected {expected_code}, got {response.status_code}\n{response.content}"
    )


def setup_for_sync(authority: str, school: str, admin_token: str):

    with open("/var/www/traeger1.txt", "r") as fp:
        traeger_IP = fp.read().strip()

    mapping = {"mapping": {str(school): str(authority)}}

    configuration = {
        "name": str(authority),
        "url": f"https://{traeger_IP}/ucsschool/kelvin/v1/",
        "active": True,
        "plugins": ["kelvin"],
        "plugin_configs": {
            "kelvin": {
                "username": "Administrator",
                "password": "univention",
                "mapping": {
                    "users": {
                        "firstname": "firstname",
                        "lastname": "lastname",
                        "username": "name",
                        "disabled": "disabled",
                        "mailPrimaryAddress": "email",
                        "school": "school",
                        "schools": "schools",
                        "school_classes": "school_classes",
                        "title": "title",
                        "displayName": "displayName",
                        "userexpiry": "expiration_date",
                        "phone": "phone",
                        "roles": "roles",
                        "ucsschoolRecordUID": "record_uid",
                        "ucsschoolSourceUID": "source_uid",
                    },
                    "school_classes": {
                        "name": "name",
                        "description": "description",
                        "school": "school",
                        "users": "users",
                    },
                },
                "sync_password_hashes": True,
                "ssl_context": {"check_hostname": False},
            }
        },
    }

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }
    mapping_response = requests.put(
        "http://sender/ucsschool-id-connector/api/v1/school_to_authority_mapping",
        headers=headers,
        data=json.dumps(mapping),
    )
    assert mapping_response.status_code == 200, faulty_request_response(mapping_response, 200)  # nosec

    config_response = requests.post(
        "http://sender/ucsschool-id-connector/api/v1/school_authorities",
        headers=headers,
        json=configuration,
    )
    if config_response.status_code == 400:
        assert "already exists" in config_response.text
    else:
        assert config_response.status_code == 201, faulty_request_response(config_response, 201)  # nosec
