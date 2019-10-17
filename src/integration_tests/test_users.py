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

import pytest
import requests
import time
from urllib.parse import urljoin
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def wait_for_status_code(method, url, status_code, headers=None, json=None, timeout=10):
    """
    Sends defined request repeatedly until the desired status code is returned or the timeout occurs.
    :param method: The requests method to use
    :param url: The url to request
    :param status_code: The desired status code to wait for
    :param headers: The headers of the request
    :param json: The json data of the request
    :param timeout: The timeout
    :return: Tuple[bool, response], with bool being True if desired status code was reached, otherwise False
    """
    start = time.time()
    result = (False, None)
    while (time.time() - start) < timeout:
        headers = {} if not headers else headers
        json = {} if not json else json
        response = method(url, headers=headers, json=json, verify=False)
        if response.status_code == status_code:
            return True, response
        result = (False, response)
    return result


@pytest.mark.asyncio
async def test_create_user(make_school_authority, make_host_user, headers, school_auth_config):
    """
    Tests if id_sync distributes a newly created User to the correct school authorities.
    """
    school_auth1 = make_school_authority(**school_auth_config(1))
    school_auth2 = make_school_authority(**school_auth_config(2))
    # TODO: Setup mapping (DEMOSCHOOL to authority1)
    user = make_host_user()
    auth1_url = urljoin(urljoin(school_auth1.url, 'users'), user['name'])
    auth2_url = urljoin(urljoin(school_auth2.url, 'users'), user['name'])
    result = wait_for_status_code(requests.get, auth1_url, 200,
                                  headers=headers(school_auth1.password.get_secret_value()))
    assert result[0]
    user_remote = result[1].json()
    # TODO: check all attributes!
    assert user_remote.name == user['name']
    assert user_remote.resource_uid == user['resource_uid']
    assert user_remote.source_uid == user['source_uid']
    result = wait_for_status_code(requests.get, auth2_url, 404,
                                  headers=headers(school_auth2.password.get_secret_value()))
    assert result[0]


@pytest.mark.asyncio
async def test_delete_user(make_school_authority, make_host_user, resource_url, host_bb_token, headers,
                           school_auth_config):
    """
    Tests if id_sync distributes the deletion of an existing user correctly.
    """
    school_auth1 = make_school_authority(**school_auth_config(1))
    school_auth2 = make_school_authority(**school_auth_config(2))
    # TODO: Setup mapping (DEMOSCHOOL to authority1)
    user = make_host_user()
    auth1_url = urljoin(urljoin(school_auth1.url, 'users'), user['name'])
    result = wait_for_status_code(requests.get, auth1_url, 200,
                                  headers=headers(school_auth1.password.get_secret_value()))
    assert result[0]
    result = requests.delete(urljoin(resource_url('users'), user['name']),
                             headers=headers(host_bb_token), verify=False)
    assert result.status_code == 204
    result = wait_for_status_code(requests.get, auth1_url, 404,
                                  headers=headers(school_auth1.password.get_secret_value()))
    assert result[0]


@pytest.mark.asyncio
async def test_modify_user(make_school_authority, make_host_user, headers, resource_url, host_bb_token,
                           school_auth_config):
    """
    Tests if the modification of a user is properly distributed to the school authority
    """
    school_auth1 = make_school_authority(**school_auth_config(1))
    school_auth2 = make_school_authority(**school_auth_config(2))
    # TODO: Setup mapping (DEMOSCHOOL to authority1)
    user = make_host_user()
    auth1_url = urljoin(urljoin(school_auth1.url, 'users'), user['name'])
    result = wait_for_status_code(requests.get, auth1_url, 200,
                                  headers=headers(school_auth1.password.get_secret_value()))
    assert result[0]
    # Modify user
    resp = requests.patch(urljoin(resource_url('users'), user['name'] + '/'), verify=False,
                          headers=headers(host_bb_token), json={'disabled': not user['disabled']})
    # Check if user was modified
    time.sleep(10)
    auth1_url = urljoin(urljoin(school_auth1.url, 'users'), user['name'])
    result = wait_for_status_code(requests.get, auth1_url, 200,
                                  headers=headers(school_auth1.password.get_secret_value()))
    assert result[0]
    remote_user = result[1].json()
    assert remote_user.disabled != user.disabled  # Just an example to check
