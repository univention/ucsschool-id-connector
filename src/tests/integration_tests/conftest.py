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

from typing import Any, Dict, List
from urllib.parse import urljoin

import pytest
import os
import json
import string
import random
import requests
from pydantic import UrlStr

from id_sync.models import SchoolAuthorityConfiguration
from id_sync.utils import get_ucrv
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


@pytest.fixture(scope='session')
def school_auth_config(docker_hostname: str):
    """
    Fixture to create configurations for school authorities. It expects a specific environment for the integration
    tests and can provide a maximum of two distinct configurations.
    """
    requested_data = dict()
    for fnf in ('bb-api-IP_traeger', 'bb-api-key_traeger'):
        for i in ('1', '2'):
            resp = requests.get(urljoin('http://' + docker_hostname, fnf + i + '.txt'))
            assert resp.status_code == 200
            requested_data[fnf + i] = resp.text.strip('\n')

    def _school_auth_config(auth_nr: int) -> Dict[str, str]:
        """
        Generates a configuration for a school authority.
        :param auth_nr: Request the config for either school authority auth1 or school authority auth2
        :return: The school authority configuration in dictionary form
        """
        assert 0 < auth_nr < 3
        config = {
            'name': 'auth' + str(auth_nr),
            'url': 'https://' + requested_data['bb-api-IP_traeger' + str(auth_nr)] + '/api-bb/',
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
    """
    TODO: Replace with Faker
    """

    def _func(ints=True):
        name = list(string.ascii_letters)
        if ints:
            name.extend(list(string.digits))
        random.shuffle(name)
        return "".join(name[: random.randint(8, 10)])

    return _func


@pytest.fixture
def random_int():
    """
    TODO: Replace with Faker
    """

    def _func(start=0, end=12):
        return random.randint(start, end)

    return _func


@pytest.fixture()
def req_headers():
    """
    Fixture to create request headers for BB-API and id-sync-API requests
    """

    def _req_headers(token: str = '', bearer: str = '', accept: str = '', content_type: str = '') -> Dict[str, str]:
        """
        Creates a dictionary containing the specified headers
        :param token: The secret for creating the Authorization: Token header
        :param bearer: The secret for creating the Authorization: Bearer header. Overrides Token if both are present
        :param accept: The value of the accept header
        :param content_type: The value of the Content-Type header
        :return: The dict containing all specified headers
        """
        headers = dict()
        if token:
            headers['Authorization'] = 'Token {}'.format(token)
        if bearer:
            headers['Authorization'] = 'Bearer {}'.format(bearer)
        if accept:
            headers['accept'] = accept
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    return _req_headers


@pytest.fixture()
def bb_api_url():
    """
    Fixture to create BB-API resource URLs.
    """

    def _bb_api_url(hostname: str, resource: str, entity: str = '') -> str:
        """
        Creates a BB-API resource URL
        :param hostname: The APIs hostname
        :param resource: The resource to query (schools, users, roles)
        :param entity: If given it builds the URL for the specific resource entity
        :return: The BB-API URL
        """
        if hostname.endswith('api-bb/'):
            return urljoin(hostname, '{}/{}'.format(resource, entity))
        return urljoin('https://{}/api-bb/'.format(hostname), '{}/{}/'.format(resource, entity))

    return _bb_api_url


@pytest.fixture(scope='session')
def docker_hostname():
    """
    The hostname of the docker containers host system.
    """
    return os.environ['docker_host_name']


@pytest.fixture()
async def source_uid() -> str:
    """
    The source UID as specified in the id-sync App settings.
    """
    return await get_ucrv('id-sync/source_uid')


@pytest.fixture(scope='session')
def host_bb_token(docker_hostname: str) -> str:
    """
    Returns a valid token for the BB-API of the containers host system.
    """
    resp = requests.get(urljoin('http://' + docker_hostname + '/', 'bb-api-key_sender.txt'))
    assert resp.status_code == 200
    return resp.text.strip('\n')


@pytest.fixture(scope='session')
def host_id_sync_token(docker_hostname: str) -> str:
    """
    Returns a valid token for the id-sync HTTP-API.
    """
    req_headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(urljoin('https://' + docker_hostname, 'id-sync/api/token'), verify=False,
                             data=dict(username='Administrator', password='univention'),
                             headers=req_headers)
    assert response.status_code == 200
    return response.json()['access_token']


@pytest.fixture()
async def make_school_authority(host_id_sync_token: str, docker_hostname: str,
                                req_headers) -> SchoolAuthorityConfiguration:
    """
    Fixture factory to create (and at the same time save) school authorities.
    They will be deleted automatically when the fixture goes out of scope
    """
    created_authorities = list()
    headers = req_headers(bearer=host_id_sync_token, accept='application/json', content_type='application/json')

    def _make_school_authority(name: str, url: UrlStr, password: str,
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
                             verify=False, json=json_data, headers=headers)
        assert resp.status_code == 201
        school_authority = SchoolAuthorityConfiguration(name=name, url=url, password=password, mapping=mapping,
                                                        password_target_attribute='id_sync_pw')
        created_authorities.append(school_authority.name)
        return school_authority

    yield _make_school_authority

    for school_authority_name in created_authorities:
        response = requests.delete(
            urljoin('https://' + docker_hostname, 'id-sync/api/v1/school_authorities/' + school_authority_name),
            verify=False, headers=headers)


@pytest.fixture()
def save_mapping(docker_hostname: str, req_headers, host_id_sync_token: str):
    """
    Fixture to save a ou to school authority mapping in id-sync. Mapping gets deleted if the fixture goes out of scope
    """
    headers = req_headers(bearer=host_id_sync_token, accept='application/json', content_type='application/json')

    def _save_mapping(mapping: Dict[str, str]):
        """
        Saves the specified mapping via HTTP-API
        :param mapping: The mapping
        """
        response = requests.put(
            urljoin('https://{}'.format(docker_hostname), 'id-sync/api/v1/school_to_authority_mapping'),
            verify=False, json=dict(mapping=mapping),
            headers=headers)
        assert response.json() == dict(mapping=mapping)

    yield _save_mapping

    response = requests.put(urljoin('https://{}'.format(docker_hostname), 'id-sync/api/v1/school_to_authority_mapping'),
                            verify=False, json=dict(mapping=dict()),
                            headers=headers)
    assert response.json() == dict(mapping=dict())


@pytest.fixture()
def create_schools(random_name, docker_hostname, bb_api_url, host_bb_token, req_headers):
    """
    Fixture factory to create OUs. The OUs are cached during multiple test runs to save development time.
    """
    mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth-school-mapping.json')
    auth_school_mapping = dict()
    if os.path.exists(mapping_file):
        with open(mapping_file, 'r') as fp:
            auth_school_mapping = json.load(fp)
    else:
        os.mknod(mapping_file)

    def _create_schools(school_authorities: [(SchoolAuthorityConfiguration, int)]) -> Dict[str, List[str]]:
        """
        Creates a number of OUs per school authority as specified. If OUs are present already they are reused.
        The OUs are created on the host system as well as the specified authority.
        :param school_authorities: A list of (school_authority, amount of OUs) tuples.
        :return: The mapping from school_authority to OUs
        """
        for auth, amount in school_authorities:
            ous = list()
            if auth.name in auth_school_mapping:
                ous = ['testou-{}'.format(random_name()) for i in
                       range(amount - len(auth_school_mapping[auth.name]))]
            else:
                ous = ['testou-{}'.format(random_name()) for i in range(amount)]
                auth_school_mapping[auth.name] = list()
            for ou in ous:
                resp = requests.post(bb_api_url(docker_hostname, 'schools'), verify=False,
                                     headers=req_headers(token=host_bb_token, content_type='application/json'),
                                     json={'name': ou, 'display_name': ou})
                assert resp.status_code == 201
                resp = requests.post(bb_api_url(auth.url, 'schools'), verify=False,
                                     headers=req_headers(token=auth.password.get_secret_value(),
                                                         content_type='application/json'),
                                     json={'name': ou, 'display_name': ou})
                assert resp.status_code == 201
                auth_school_mapping[auth.name].append(ou)
        with open(mapping_file, 'w') as fp:
            fp.truncate()
            json.dump(auth_school_mapping, fp)
        return auth_school_mapping

    return _create_schools


@pytest.fixture()
async def make_host_user(host_bb_token: str, random_name, random_int, bb_api_url,
                         source_uid: str, req_headers, docker_hostname: str):
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
        :return: The json used to create the user via the API
        """
        firstname = random_name()
        lastname = random_name()
        user_data = {
            'name': 'test{}'.format(random_name()),
            'birthday': "19{}-0{}-{}{}".format(
                random_int(10, 99),
                random_int(1, 9),
                random_int(0, 2),
                random_int(1, 8)
            ),
            'disabled': False,
            'firstname': firstname,
            'lastname': lastname,
            'record_uid': '{}.{}'.format(firstname, lastname),
            'roles': [bb_api_url(docker_hostname, 'roles', role) for role in roles],
            'school': bb_api_url(docker_hostname, 'schools', ous[0]),
            'school_classes': {} if roles == ('staff',) else dict(
                (ou, sorted([random_name(4), random_name(4)]))
                for ou in ous
            ),
            'schools': [bb_api_url(docker_hostname, 'schools', ou) for ou in ous],
            'source_uid': source_uid,
        }
        resp = requests.post(bb_api_url(docker_hostname, 'users'),
                             headers=req_headers(token=host_bb_token, content_type='application/json'), json=user_data,
                             verify=False)
        print(resp.json())
        assert resp.status_code == 201
        response_user = resp.json()
        created_users.append(response_user)
        return user_data

    yield _make_host_user

    for user in created_users:
        requests.delete(bb_api_url(docker_hostname, 'users', user['name']),
                        headers=req_headers(token=host_bb_token), verify=False)
