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

from typing import Any, Dict, Callable
from urllib.parse import urljoin

import pytest
import os
import string
import random
import requests
from pydantic import SecretStr, UrlStr

from id_sync.models import SchoolAuthorityConfiguration
from id_sync.utils import get_ucrv
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


@pytest.fixture(scope='session')
def school_auth_config(docker_hostname: str):
    requested_data = dict()
    for fnf in ('bb-api-IP_traeger', 'bb-api-key_traeger'):
        for i in ('1', '2'):
            resp = requests.get(urljoin('http://' + docker_hostname, fnf + i + '.txt'))
            assert resp.status_code == 200
            requested_data[fnf + i] = resp.text.strip('\n')

    def _school_auth_config(auth_nr: int):
        assert 0 < auth_nr < 3
        config = {
            'name': 'auth' + str(auth_nr),
            'url': 'https://' + requested_data['bb-api-IP_traeger' + str(auth_nr)] + '/api-bb',
            'password': requested_data['bb-api-key_traeger' + str(auth_nr)],
            'mapping': {
                'firstname': 'firstname',
                'lastname': 'lastname',
                'username': 'name',
                'disabled': 'disabled',
                'mailPrimaryAddress': 'email',
                'e-mail': 'email',
                'birthday': 'birthday',
                'password': 'password',
                'school': 'school',
                'schools': 'schools',
                'school_classes': 'school_classes',
                'source_uid': 'source_uid',
                'roles': 'roles',
                'title': 'title',
                'displayName': 'displayName',
                'userexpiry': 'userexpiry',
                'phone': 'phone',
                'record_uid': 'record_uid'
            }
        }
        return config

    yield _school_auth_config


@pytest.fixture
def random_name():
    def _func(ints=True):
        name = list(string.ascii_letters)
        if ints:
            name.extend(list(string.digits))
        random.shuffle(name)
        return "".join(name[: random.randint(8, 10)])

    return _func


@pytest.fixture
def random_int():
    def _func(start=0, end=12):
        return random.randint(start, end)

    return _func


@pytest.fixture()
def headers():
    """
    Fixture that creates the headers dict for requests to the BB-API for you.
    """

    def _headers(secret: str, auth_type: str = 'Token') -> Dict[str, str]:
        """
        Create the headers dict for the BB-API
        :param secret: The secret to put into the Authorization header. Token: is prepended.
        :param auth_type: The type of authentication token to specify in Authorization header.
        :return: The header dict
        """
        return {
            'Authorization': auth_type + ' ' + secret,
            'Content-Type': 'application/json'
        }

    return _headers


@pytest.fixture()
async def resource_url(docker_hostname: str):
    def _resource_url(resource: str) -> str:
        """
        Returns a resource URL for the docker containers hosts BB-API
        :param resource: The resource to generate the URL for
        :return: The resource endpoint URL
        """
        api_root = urljoin('https://' + docker_hostname, 'api-bb/')
        return urljoin(api_root, resource) + '/'

    return _resource_url


@pytest.fixture(scope='session')
def docker_hostname():
    return os.environ['docker_host_name']


@pytest.fixture()
async def source_uid():
    return await get_ucrv('id-sync/source_uid')


@pytest.fixture(scope='session')
def host_bb_token(docker_hostname):
    """
    Returns a valid token for the BB-API of the containers host system.
    :return: A valid API token
    """
    resp = requests.get(urljoin('http://' + docker_hostname, 'bb-api-key_sender.txt'))
    assert resp.status_code == 200
    return resp.text.strip('\n')


@pytest.fixture(scope='session')
def host_id_sync_token(docker_hostname):
    """
    Returns a valid token for the id-sync HTTP-API
    """
    req_headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(urljoin('https://' + docker_hostname, 'id-sync/api/token'), verify=False,
                             data=dict(username='Administrator', password='univention'),
                             headers=req_headers)
    assert response.status_code == 200
    return response.json()['access_token']


@pytest.fixture()
async def make_school_authority(host_id_sync_token: str, docker_hostname: str, headers):
    """
    Fixture factory to create (and at the same time save) school authorities.
    They will be deleted automatically when the fixture goes out of scope
    """
    created_authorities = list()
    req_headers = {
        'Authorization': 'Bearer ' + host_id_sync_token,
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    def _make_school_authority(name: str, url: UrlStr, password: SecretStr,
                               mapping: Dict[str, Any]) -> SchoolAuthorityConfiguration:
        """
        Creates and saves a school authority
        :param name: The school authorities name
        :param url: The url for the school authorities endpoint
        :param password: The secret to access the school authorities endpoint
        :param mapping: The school authorities mapping
        :return: A saved school authority
        """
        json_data = {
            'name': name,
            'url': url,
            'password': password,
            'active': True,
            'mapping': mapping,
            'passwords_target_attribute': 'id_sync_pw'
        }
        resp = requests.post(urljoin('https://' + docker_hostname, 'id-sync/api/v1/school_authorities'),
                             verify=False, json=json_data, headers=req_headers)
        assert resp.status_code == 201
        school_authority = SchoolAuthorityConfiguration(name=name, url=url, password=password, mapping=mapping,
                                                        password_target_attribute='id_sync_pw')
        created_authorities.append(school_authority.name)
        return school_authority

    yield _make_school_authority

    for school_authority_name in created_authorities:
        response = requests.delete(
            urljoin('https://' + docker_hostname, 'id-sync/api/v1/school_authorities/' + school_authority_name),
            verify=False, headers=req_headers)


@pytest.fixture()
async def make_host_user(host_bb_token: str, random_name, random_int, resource_url: Callable[[str], str], source_uid: str, headers):
    """
    Fixture factory to create users on the host system. They are created via the BB-API and
    automatically removed when the fixture goes out of scope.
    """
    created_users = list()

    def _make_host_user(roles=('student',), ous=('DEMOSCHOOL',)):
        """
        Creates a user on the hosts UCS system via BB-API
        :param roles: The new users roles
        :param ous: The new users ous
        :return: The json returned by the POST request
        """
        user_data = {
            'name': 'test{}'.format(random_name()),
            'birthday': "19{}-0{}-{}{}".format(
                random_int(10, 99),
                random_int(1, 9),
                random_int(0, 2),
                random_int(1, 8)
            ),
            'disabled': False,
            'firstname': random_name(),
            'lastname': random_name(),
            'record_uid': random_name(),
            'roles': [urljoin(resource_url('roles'), role + "/") for role in roles],
            'school': urljoin(resource_url('schools'), ous[0] + "/"),
            'school_classes': {} if roles == ('staff',) else dict(
                (ou, sorted([random_name(4), random_name(4)]))
                for ou in ous
            ),
            'schools': [urljoin(resource_url('schools'), ou + "/") for ou in ous],
            'source_uid': source_uid,
        }
        resp = requests.post(resource_url('users'), headers=headers(host_bb_token), json=user_data, verify=False)
        assert resp.status_code == 201
        response_user = resp.json()
        created_users.append(response_user)
        return response_user

    yield _make_host_user

    for user in created_users:
        requests.delete(urljoin(resource_url('users'), user['name']),
                        headers={'Authorization': 'Token ' + host_bb_token}, verify=False)
