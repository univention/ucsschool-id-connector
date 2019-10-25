# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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

import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import faker
import pytest
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
fake = faker.Faker()


def compare_user(source: Dict[str, Any], other: Dict[str, Any], to_check=()):
    """
    This function compares two dictionaries. Specifically it checks if all
    key-value pairs from the source also exist in the other dictionary. It
    does not assert all key-value pairs from the other dictionary to be in the
    source!

    :param source: The original dictionary
    :param other: The dictionary to check against the original source
    :param to_check: The keys to check.
    """
    if len(to_check) == 0:
        to_check = [
            "disabled",
            "firstname",
            "lastname",
            "name",
            "record_uid",
            "school_classes",
            "source_uid",
        ]
    for key in to_check:
        assert source[key] == other[key]


def wait_for_status_code(
    method, url, status_code, headers=None, json=None, timeout=10, raise_assert=True
) -> Tuple[bool, Optional[requests.Response]]:
    """
    Sends defined request repeatedly until the desired status code is returned
    or the timeout occurs.

    :param method: The requests method to use
    :param url: The url to request
    :param status_code: The desired status code to wait for
    :param headers: The headers of the request
    :param json: The json data of the request
    :param int timeout: The timeout
    :param bool raise_assert: whether to raise an AssertionError if the desired
        status code was not reached
    :return: Tuple[bool, response], with bool being True if desired status code
        was reached, otherwise False
    """
    start = time.time()
    response = None
    while (time.time() - start) < timeout:
        headers = headers or {}
        json = json or {}
        response = method(url, headers=headers, json=json, verify=False)
        if response.status_code == status_code:
            return True, response
        time.sleep(1)
    if raise_assert:
        raise AssertionError(
            f"Status {None if response is None else response.status_code} "
            f"(reason: {None if response is None else response.reason}) for "
            f"{method.__name__.upper()} {url!r} using headers={headers!r}"
            f" and json={json!r}."
        )
    return False, response


@pytest.mark.asyncio
async def test_create_user(
    make_school_authority,
    make_host_user,
    req_headers,
    school_auth_config,
    save_mapping,
    create_schools,
    bb_api_url,
):
    """
    Tests if id_sync distributes a newly created User to the correct school
    authorities.
    """
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
    mapping = {
        ou_auth1: school_auth1.name,
        ou_auth1_2: school_auth1.name,
        ou_auth2: school_auth2.name,
    }
    await save_mapping(mapping)
    print(f"Mapping: {mapping!r}")
    for ous in ((ou_auth1,), (ou_auth1, ou_auth1_2), (ou_auth1, ou_auth2)):
        print(f"Creating user in ous={ous!r}...")
        user = make_host_user(ous=ous)
        auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
        auth2_url = bb_api_url(school_auth2.url, "users", user["name"])
        print(
            f"Created user {user['name']!r}, looking for it in auth1 at {auth1_url!r}..."
        )
        result = wait_for_status_code(
            requests.get,
            auth1_url,
            200,
            headers=req_headers(
                token=school_auth1.password.get_secret_value(),
                content_type="application/json",
            ),
        )
        user_remote = result[1].json()
        # TODO: check all attributes!
        print(f"Found user {user_remote['name']!r}, checking its attributes...")
        compare_user(user, user_remote, ["firstname"])
        if ou_auth2 in ous:
            print(f"User should also be in OU2 ({ou_auth2!r}), checking...")
            result = wait_for_status_code(
                requests.get,
                auth2_url,
                200,
                headers=req_headers(
                    token=school_auth2.password.get_secret_value(),
                    content_type="application/json",
                ),
            )
            user_remote = result[1].json()
            # TODO: check all attributes!
            compare_user(user, user_remote, ["firstname"])
        else:
            print(f"User should NOT be in OU2 ({ou_auth2!r}), checking...")
            wait_for_status_code(
                requests.get,
                auth2_url,
                404,
                headers=req_headers(
                    token=school_auth2.password.get_secret_value(),
                    content_type="application/json",
                ),
            )


@pytest.mark.asyncio
async def test_delete_user(
    make_school_authority,
    make_host_user,
    host_bb_token,
    req_headers,
    school_auth_config,
    save_mapping,
    create_schools,
    bb_api_url,
    docker_hostname,
    http_request,
):
    """
    Tests if id_sync distributes the deletion of an existing user correctly.
    """
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
    mapping = {
        ou_auth1: school_auth1.name,
        ou_auth1_2: school_auth1.name,
        ou_auth2: school_auth2.name,
    }
    await save_mapping(mapping)
    print(f"Mapping: {mapping!r}")
    user = make_host_user(ous=(ou_auth1, ou_auth2))
    auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
    auth2_url = bb_api_url(school_auth2.url, "users", user["name"])
    print(
        f"Created user {user['name']!r} in sender. Looking for it now in "
        f"ou_auth1 at {auth1_url!r}..."
    )
    wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    print(
        f"Found user {user['name']!r} in ou_auth1. Looking for it now in "
        f"ou_auth2 at {auth2_url!r}..."
    )
    wait_for_status_code(
        requests.get,
        auth2_url,
        200,
        headers=req_headers(
            token=school_auth2.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    print(f"Deleting user {user['name']!r} in sender...")
    http_request(
        "delete",
        bb_api_url(docker_hostname, "users", user["name"]),
        headers=req_headers(token=host_bb_token, content_type="application/json"),
        verify=False,
        expected_statuses=(204,),
    )
    print(
        f"User {user['name']!r} was deleted in sender, waiting for it to "
        f"disappear in ou_auth1..."
    )
    wait_for_status_code(
        requests.get,
        auth1_url,
        404,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    print(
        f"User {user['name']!r} disappeared in ou_auth1, waiting for it to "
        f"also disappear in ou_auth2..."
    )
    wait_for_status_code(
        requests.get,
        auth2_url,
        404,
        headers=req_headers(
            token=school_auth2.password.get_secret_value(),
            content_type="application/json",
        ),
    )


@pytest.mark.asyncio
async def test_modify_user(
    make_school_authority,
    make_host_user,
    req_headers,
    bb_api_url,
    host_bb_token,
    school_auth_config,
    save_mapping,
    create_schools,
    docker_hostname,
    http_request,
):
    """
    Tests if the modification of a user is properly distributed to the school
    authority
    """
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
    await save_mapping(
        {
            ou_auth1: school_auth1.name,
            ou_auth1_2: school_auth1.name,
            ou_auth2: school_auth2.name,
        }
    )
    user = make_host_user(ous=[ou_auth1])
    # check user exists on sender
    wait_for_status_code(
        requests.get,
        bb_api_url(docker_hostname, "users", user["name"]),
        200,
        headers=req_headers(token=host_bb_token, content_type="application/json"),
    )
    # check user exists on auth1
    auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
    wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    # Modify user
    new_value = {
        "firstname": fake.first_name(),
        "lastname": fake.last_name(),
        "disabled": not user["disabled"],
        "birthday": fake.date_of_birth(minimum_age=6, maximum_age=67).strftime(
            "%Y-%m-%d"
        ),
    }
    response = http_request(
        "patch",
        bb_api_url(docker_hostname, "users", user["name"]),
        verify=False,
        headers=req_headers(token=host_bb_token, content_type="application/json"),
        json=new_value,
    )
    user_on_host = response.json()
    assert user_on_host["disabled"] == new_value["disabled"]
    # Check if user was modified
    time.sleep(10)
    result = wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    remote_user = result[1].json()
    assert remote_user["disabled"] == new_value["disabled"]
    assert remote_user["firstname"] == new_value["firstname"]
    assert remote_user["lastname"] == new_value["lastname"]
    assert remote_user["birthday"] == new_value["birthday"]


@pytest.mark.asyncio
async def test_class_change(
    make_school_authority,
    school_auth_config,
    create_schools,
    save_mapping,
    make_host_user,
    bb_api_url,
    req_headers,
    docker_hostname,
    host_bb_token,
    random_name,
    http_request,
):
    """
    Tests if the modification of a users class is properly distributed by id-sync.
    """
    school_auth1 = await make_school_authority(**school_auth_config(1))
    auth_school_mapping = create_schools([(school_auth1, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    await save_mapping({ou_auth1: school_auth1.name})
    user = make_host_user(ous=[ou_auth1])
    auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
    wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    new_value = {"school_classes": {ou_auth1: [random_name()]}}
    http_request(
        "patch",
        bb_api_url(docker_hostname, "users", user["name"]),
        verify=False,
        headers=req_headers(token=host_bb_token, content_type="application/json"),
        json_data=new_value,
    )
    time.sleep(10)
    result = wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    remote_user = result[1].json()
    assert remote_user["school_classes"] == new_value


@pytest.mark.asyncio
async def test_school_change(
    make_school_authority,
    school_auth_config,
    create_schools,
    save_mapping,
    make_host_user,
    bb_api_url,
    req_headers,
    docker_hostname,
    host_bb_token,
    random_name,
    http_request,
):
    """
    Tests if the modification of a users school is properly distributed by id-sync.
    """
    school_auth1 = await make_school_authority(**school_auth_config(1))
    auth_school_mapping = create_schools([(school_auth1, 2)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    await save_mapping({ou_auth1: school_auth1.name, ou_auth1_2: school_auth1.name})
    user = make_host_user(ous=[ou_auth1])
    auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
    wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    new_value = {
        "school_classes": {ou_auth1_2: [random_name()]},
        "school": bb_api_url(docker_hostname, "schools", ou_auth1_2),
        "schools": [bb_api_url(docker_hostname, "schools", ou_auth1_2)],
    }
    http_request(
        "patch",
        bb_api_url(docker_hostname, "users", user["name"]),
        verify=False,
        headers=req_headers(token=host_bb_token, content_type="application/json"),
        json_data=new_value,
    )
    time.sleep(10)
    auth1_url = bb_api_url(school_auth1.url, "users", user["name"])
    result = wait_for_status_code(
        requests.get,
        auth1_url,
        200,
        headers=req_headers(
            token=school_auth1.password.get_secret_value(),
            content_type="application/json",
        ),
    )
    remote_user = result[1].json()
    assert urlsplit(remote_user["school"]).path == urlsplit(new_value["school"]).path
    assert remote_user["school_classes"] == new_value["school_classes"]
    assert remote_user["schools"] == new_value["schools"]
