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

import pytest
import requests
from utils import faulty_request_response


def test_admin_api_login(udm, make_dn, hostname):
    admin_group = make_dn("cn=ucsschool-id-connector-admins", "groups")
    user_module = udm.get("users/user")
    admin_user = user_module.get(make_dn("uid=Administrator", "users"))
    assert admin_group in admin_user.props.groups

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
    assert response.status_code == 200, faulty_request_response(response, 200)  # nosec


@pytest.mark.parametrize(
    "username, password",
    [
        ["Administrator", "notArealPassword"],
        ["NotAnAdmin", "univention"],
        ["NotAnAdmin", "notArealPassword"],
    ],
)
def test_api_login_faulty_credentials(hostname, username, password):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "",
        "username": username,
        "password": password,
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    response = requests.post(
        f"https://{hostname}/ucsschool-id-connector/api/token", headers=headers, data=data
    )
    assert response.status_code == 401, faulty_request_response(response, 401)  # nosec


def test_create_and_patch_empty_school_authority(admin_token, hostname, random_school_name):
    pt_name = random_school_name

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}",
    }
    create_data = json.dumps(
        {
            "name": pt_name,
            "active": True,
            "url": "http://example.com",
            "plugins": [],
            "plugin_configs": {},
        }
    )
    post_response = requests.post(
        f"https://{hostname}/ucsschool-id-connector/api/v1/school_authorities",
        headers=headers,
        data=create_data,
    )
    assert post_response.status_code == 201, faulty_request_response(post_response, 201)  # nosec

    patch_data = json.dumps({"plugin_configs": {"foo": {"bar": 123}}})
    patch_response = requests.patch(
        f"https://{hostname}/ucsschool-id-connector/api/v1/school_authorities/{pt_name}",
        headers=headers,
        data=patch_data,
    )
    assert patch_response.status_code == 200, faulty_request_response(patch_response, 200)

    headers.pop("Content-Type")
    queue_response = requests.get(
        f"https://{hostname}/ucsschool-id-connector/api/v1/queues", headers=headers
    )
    assert queue_response.status_code == 200, faulty_request_response(queue_response, 200)  # nosec

    queue_item = {"name": pt_name, "head": "", "length": 0, "school_authority": pt_name}

    assert queue_item in queue_response.json()

    headers["accept"] = "*/*"

    delete_response = requests.delete(
        f"https://{hostname}/ucsschool-id-connector/api/v1/school_authorities/{pt_name}",
        headers=headers,
    )
    assert delete_response.status_code == 204, faulty_request_response(delete_response, 204)

    queue_response = requests.get(
        f"https://{hostname}/ucsschool-id-connector/api/v1/queues", headers=headers
    )
    assert queue_response.status_code == 200, faulty_request_response(queue_response, 200)

    assert queue_item not in queue_response.json()

    headers["accept"] = "application/json"
    headers["Content-Type"] = "application/json"

    put_data = json.dumps({"mapping": {"demoschool": pt_name}})

    put_response = requests.put(
        f"https://{hostname}/ucsschool-id-connector/api/v1/school_to_authority_mapping",
        headers=headers,
        data=put_data,
    )
    assert put_response.status_code == 200, faulty_request_response(put_response, 200)
