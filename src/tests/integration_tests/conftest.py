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

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urljoin

import faker
import pytest
import requests
from pydantic import UrlStr
from urllib3.exceptions import InsecureRequestWarning

from ucsschool_id_connector.config_storage import ConfigurationStorage
from ucsschool_id_connector.constants import APP_ID, OUT_QUEUE_TOP_DIR
from ucsschool_id_connector.models import SchoolAuthorityConfiguration
from ucsschool_id_connector.utils import get_ucrv

try:
    from simplejson.errors import JSONDecodeError
except ImportError:  # pragma: no cover
    JSONDecodeError = ValueError


fake = faker.Faker()
AUTH_SCHOOL_MAPPING_PATH: Path = Path(__file__).parent / "auth-school-mapping.json"

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


@pytest.fixture
def http_request():
    def _func(
        method: str,
        url: str,
        params: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        json_data: Dict[str, Any] = None,
        verify: bool = False,
        expected_statuses: Iterable[int] = (200,),
    ) -> requests.Response:
        req_meth = getattr(requests, method)
        response = req_meth(
            url, params=params, headers=headers, json=json_data, verify=verify
        )
        try:
            msg = response.json()
        except JSONDecodeError:
            msg = (
                "<no JSON>"
                if response.status_code in expected_statuses
                else response.text
            )
        msg = (
            f"Status {response.status_code} (reason: {response.reason}) for "
            f"{method.upper()} {url!r} using headers={headers!r} and "
            f"json_data={json_data!r} -> msg: {msg}."
        )
        assert response.status_code in expected_statuses, msg
        print(msg)
        return response

    return _func


@pytest.fixture(scope="session")
def school_auth_config(docker_hostname: str):
    """
    Fixture to create configurations for school authorities. It expects a
    specific environment for the integration tests and can provide a maximum
    of two distinct configurations.
    """
    requested_data = dict()
    for fnf in ("bb-api-IP_traeger", "bb-api-key_traeger"):
        for i in ("1", "2"):
            url = urljoin(f"https://{docker_hostname}", f"{fnf}{i}.txt")
            resp = requests.get(url, verify=False)
            assert resp.status_code == 200, (resp.status_code, resp.reason, url)
            requested_data[fnf + i] = resp.text.strip("\n")

    def _school_auth_config(auth_nr: int) -> Dict[str, str]:
        """
        Generates a configuration for a school authority.

        :param auth_nr: Request the config for either school authority auth1
            or school authority auth2
        :return: The school authority configuration in dictionary form
        """
        assert 0 < auth_nr < 3
        config = {
            "name": f"auth{auth_nr}",
            "url": f"https://{requested_data[f'bb-api-IP_traeger{auth_nr}']}/api-bb/",
            "password": requested_data[f"bb-api-key_traeger{auth_nr}"],
            "mapping": {
                "firstname": "firstname",
                "lastname": "lastname",
                "username": "name",
                "disabled": "disabled",
                "mailPrimaryAddress": "email",
                "e-mail": "email",
                "birthday": "birthday",
                "password": "password",
                "school": "school",
                "schools": "schools",
                "school_classes": "school_classes",
                "ucsschoolSourceUID": "source_uid",
                "roles": "roles",
                "title": "title",
                "displayName": "displayName",
                "userexpiry": "userexpiry",
                "phone": "phone",
                "ucsschoolRecordUID": "record_uid",
            },
        }
        return config

    yield _school_auth_config


@pytest.fixture()
def req_headers():
    """
    Fixture to create request headers for BB-API and
    ucsschool-id-connector-API requests.
    """

    def _req_headers(
        token: str = "", bearer: str = "", accept: str = "", content_type: str = ""
    ) -> Dict[str, str]:
        """
        Creates a dictionary containing the specified headers

        :param token: The secret for creating the Authorization: Token header
        :param bearer: The secret for creating the Authorization: Bearer
            header. Overrides Token if both are present
        :param accept: The value of the accept header
        :param content_type: The value of the Content-Type header
        :return: The dict containing all specified headers
        """
        headers = dict()
        if token:
            headers["Authorization"] = "Token {}".format(token)
        if bearer:
            headers["Authorization"] = "Bearer {}".format(bearer)
        if accept:
            headers["accept"] = accept
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    return _req_headers


@pytest.fixture()
def bb_api_url():
    """
    Fixture to create BB-API resource URLs.
    """

    def _bb_api_url(hostname: str, resource: str, entity: str = "") -> str:
        """
        Creates a BB-API resource URL

        :param hostname: The APIs hostname
        :param resource: The resource to query (schools, users, roles)
        :param entity: If given it builds the URL for the specific resource entity
        :return: The BB-API URL
        """
        if hostname.endswith("api-bb/"):
            return urljoin(hostname, f"{resource}/{entity}")
        return urljoin(f"https://{hostname}/api-bb/", f"{resource}/{entity}/")

    return _bb_api_url


@pytest.fixture()
def ucsschool_id_connector_api_url(docker_hostname):
    """
    Fixture to create UCS@school ID Connector API resource URLs.
    """

    def _ucsschool_id_connector_api_url(resource: str, entity: str = "") -> str:
        """
        Creates a UCS@school ID Connector API resource URL

        :param resource: The resource to query
        :param entity: If given it builds the URL for the specific resource entity
        :return: The UCS@school ID Connector API URL
        """
        return urljoin(
            f"https://{docker_hostname}/{APP_ID}/api/v1/", f"{resource}/{entity}"
        ).rstrip("/")

    return _ucsschool_id_connector_api_url


@pytest.fixture(scope="session")
def docker_hostname():
    """
    The hostname of the docker containers host system.
    """
    return os.environ["docker_host_name"]


@pytest.fixture()
async def source_uid() -> str:
    """
    The source UID as specified in the ucsschool-id-connector App settings.
    """
    return await get_ucrv(f"{APP_ID}/source_uid")


@pytest.fixture(scope="session")
def host_bb_token(docker_hostname: str) -> str:
    """
    Returns a valid token for the BB-API of the containers host system.
    """
    resp = requests.get(
        urljoin(f"https://{docker_hostname}/", "bb-api-key_sender.txt"), verify=False
    )
    assert resp.status_code == 200, (resp.status_code, resp.reason, resp.url)
    return resp.text.strip("\n")


@pytest.fixture(scope="session")
def host_ucsschool_id_connector_token(docker_hostname: str) -> str:
    """
    Returns a valid token for the ucsschool-id-connector HTTP-API.
    """
    req_headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.post(
        urljoin(f"https://{docker_hostname}", f"{APP_ID}/api/token"),
        verify=False,
        data=dict(username="Administrator", password="univention"),
        headers=req_headers,
    )
    assert response.status_code == 200, (
        response.status_code,
        response.reason,
        response.url,
    )
    return response.json()["access_token"]


@pytest.fixture()
async def make_school_authority(
    host_ucsschool_id_connector_token: str,
    ucsschool_id_connector_api_url,
    req_headers,
    http_request,
    school_authority_configuration,
) -> SchoolAuthorityConfiguration:
    """
    Fixture factory to create (and at the same time save) school authorities.
    They will be deleted automatically when the fixture goes out of scope
    """
    created_authorities = list()
    headers = req_headers(
        bearer=host_ucsschool_id_connector_token,
        accept="application/json",
        content_type="application/json",
    )

    async def _make_school_authority(
        name: str, url: UrlStr, password: str, mapping: Dict[str, Any]
    ) -> SchoolAuthorityConfiguration:
        """
        Creates and saves a school authority

        :param name: The school authorities name
        :param url: The url for the school authorities endpoint
        :param password: The secret to access the school authorities endpoint
        :param mapping: The school authorities mapping
        :return: A saved school authority
        """
        # try to delete possible leftovers from previous failed test
        http_request(
            "delete",
            urljoin(f"{ucsschool_id_connector_api_url('school_authorities')}/", name),
            headers=headers,
            expected_statuses=(204, 404),
        )
        # (re)create school authority configuration
        school_authority = school_authority_configuration(
            name=name,
            url=url,
            password=password,
            mapping=mapping,
            password_target_attribute="ucsschool_id_connector_pw",
        )
        config_as_dict = school_authority.dict()
        config_as_dict["password"] = school_authority.password.get_secret_value()
        url = ucsschool_id_connector_api_url("school_authorities")
        http_request(
            "post",
            url,
            json_data=config_as_dict,
            headers=headers,
            expected_statuses=(201,),
        )
        async for loaded_s_a in ConfigurationStorage.load_school_authorities():
            if (
                loaded_s_a.name == name
                and loaded_s_a.password.get_secret_value() == password
            ):
                break
        else:
            raise AssertionError(
                f"SchoolAuthorityConfiguration(name={name!r}) was not saved."
            )  # pragma: no cover
        out_queue_dir = OUT_QUEUE_TOP_DIR / name
        assert out_queue_dir.exists()

        created_authorities.append(school_authority.name)
        return school_authority

    yield _make_school_authority

    for school_authority_name in created_authorities:
        http_request(
            "delete",
            ucsschool_id_connector_api_url("school_authorities", school_authority_name),
            headers=headers,
            expected_statuses=(204, 404),
        )
        async for loaded_s_a in ConfigurationStorage.load_school_authorities():
            if loaded_s_a.name == school_authority_name:
                raise AssertionError(
                    f"SchoolAuthorityConfiguration(name={school_authority_name!r})"
                    f" was not deleted."
                )  # pragma: no cover
        out_queue_dir = OUT_QUEUE_TOP_DIR / school_authority_name
        assert not out_queue_dir.exists()


@pytest.fixture()
async def save_mapping(
    ucsschool_id_connector_api_url,
    req_headers,
    host_ucsschool_id_connector_token: str,
    http_request,
):
    """
    Fixture to save an ou to school authority mapping in ucsschool-id-connector.
    Mapping gets deleted if the fixture goes out of scope.
    """
    headers = req_headers(
        bearer=host_ucsschool_id_connector_token,
        accept="application/json",
        content_type="application/json",
    )
    ori_s2s_mapping = await ConfigurationStorage.load_school2target_mapping()
    print(f"Original s2s mapping: {ori_s2s_mapping.dict()!r}")

    async def _save_mapping(mapping: Dict[str, str]):
        """
        Saves the specified mapping via HTTP-API
        :param mapping: The mapping
        """
        response = http_request(
            "put",
            ucsschool_id_connector_api_url("school_to_authority_mapping"),
            json_data=dict(mapping=mapping),
            headers=headers,
        )
        assert response.json() == dict(mapping=mapping), (
            response.status_code,
            response.reason,
            response.url,
        )
        s2s_mapping = await ConfigurationStorage.load_school2target_mapping()
        assert mapping == s2s_mapping.mapping
        print(f"Set new s2s mapping: {s2s_mapping.dict()!r}")

    yield _save_mapping

    response = http_request(
        "put",
        ucsschool_id_connector_api_url("school_to_authority_mapping"),
        json_data=ori_s2s_mapping.dict(),
        headers=headers,
    )
    assert response.json() == ori_s2s_mapping.dict(), (
        response.status_code,
        response.reason,
        response.url,
    )
    s2s_mapping = await ConfigurationStorage.load_school2target_mapping()
    assert s2s_mapping == ori_s2s_mapping
    print(f"Restored original s2s mapping: {s2s_mapping.dict()!r}")


@pytest.fixture()
def create_schools(
    random_name, docker_hostname, bb_api_url, host_bb_token, req_headers, http_request
):
    """
    Fixture factory to create OUs. The OUs are cached during multiple test runs
    to save development time.
    """
    if AUTH_SCHOOL_MAPPING_PATH.exists():
        with AUTH_SCHOOL_MAPPING_PATH.open("r") as fp:
            auth_school_mapping = json.load(fp)
    else:
        auth_school_mapping = dict()

    def _create_schools(
        school_authorities: List[Tuple[SchoolAuthorityConfiguration, int]]
    ) -> Dict[str, List[str]]:
        """
        Creates a number of OUs per school authority as specified. If OUs are
        present already they are reused.
        The OUs are created on the host system as well as the specified authority.

        :param school_authorities: A list of (school_authority, amount of OUs) tuples.
        :return: The mapping from school_authority to OUs
        """
        for auth, amount in school_authorities:
            print(f"Creating {amount} schools for auth {auth.name!r}...")
            try:
                ous = auth_school_mapping[auth.name]
            except KeyError:
                auth_school_mapping[auth.name] = []
                ous = []
            ous.extend(
                ["testou-{}".format(random_name()) for i in range(amount - len(ous))]
            )
            print(f"Creating OUs: {ous!r}...")
            for ou in ous:
                url = bb_api_url(docker_hostname, "schools")
                response = http_request(
                    "get",
                    bb_api_url(docker_hostname, "schools", ou),
                    headers=req_headers(
                        token=host_bb_token, content_type="application/json"
                    ),
                    expected_statuses=(200, 404),
                )
                if response.status_code == 200:
                    print(f"OU {ou} exists in sender.")
                else:
                    print(f"Creating OU {ou!r} in sender ({url!r})...")
                    http_request(
                        "post",
                        url,
                        headers=req_headers(
                            token=host_bb_token, content_type="application/json"
                        ),
                        json_data={"name": ou, "display_name": ou},
                        expected_statuses=(201, 400),
                    )
                    http_request(
                        "get",
                        bb_api_url(docker_hostname, "schools", ou),
                        headers=req_headers(
                            token=host_bb_token, content_type="application/json"
                        ),
                    )
                url = bb_api_url(auth.url, "schools")
                http_request(
                    "get",
                    bb_api_url(auth.url, "schools", ou),
                    headers=req_headers(
                        token=auth.password.get_secret_value(),
                        content_type="application/json",
                    ),
                    expected_statuses=(200, 404),
                )
                if response.status_code == 200:
                    print(f"OU {ou} exists in {auth.name!r}.")
                else:
                    print(f"Creating OU {ou!r} in {auth.name!r} ({url!r})...")
                    http_request(
                        "post",
                        url,
                        headers=req_headers(
                            token=auth.password.get_secret_value(),
                            content_type="application/json",
                        ),
                        json_data={"name": ou, "display_name": ou},
                        expected_statuses=(201,),
                    )
                    http_request(
                        "get",
                        bb_api_url(auth.url, "schools", ou),
                        headers=req_headers(
                            token=auth.password.get_secret_value(),
                            content_type="application/json",
                        ),
                    )
                if ou not in auth_school_mapping[auth.name]:
                    auth_school_mapping[auth.name].append(ou)
        with AUTH_SCHOOL_MAPPING_PATH.open("w") as fp:
            json.dump(auth_school_mapping, fp)
        return auth_school_mapping

    return _create_schools


@pytest.fixture()
async def make_host_user(
    host_bb_token: str,
    random_name,
    random_int,
    bb_api_url,
    source_uid: str,
    req_headers,
    docker_hostname: str,
    http_request,
):
    """
    Fixture factory to create users on the apps host system. They are created
    via the BB-API and automatically removed when the fixture goes out of scope.
    """
    created_users = list()

    def _make_host_user(roles=("student",), ous=("DEMOSCHOOL",)):
        """
        Creates a user on the hosts UCS system via BB-API

        :param roles: The new users roles
        :param ous: The new users ous
        :return: The json used to create the user via the API
        """
        firstname = fake.first_name()
        lastname = fake.last_name()
        user_data = {
            "name": "test{}".format(fake.user_name())[:15],
            "birthday": fake.date_of_birth(minimum_age=6, maximum_age=67).strftime(
                "%Y-%m-%d"
            ),
            "disabled": False,
            "firstname": firstname,
            "lastname": lastname,
            "password": fake.password(length=15),
            "record_uid": "{}.{}".format(firstname, lastname),
            "roles": [bb_api_url(docker_hostname, "roles", role) for role in roles],
            "school": bb_api_url(docker_hostname, "schools", ous[0]),
            "school_classes": {}
            if roles == ("staff",)
            else dict((ou, sorted([random_name(4), random_name(4)])) for ou in ous),
            "schools": [bb_api_url(docker_hostname, "schools", ou) for ou in ous],
            "source_uid": source_uid,
        }
        print(f"Creating user {user_data['name']!r} in source system...")
        resp = http_request(
            "post",
            bb_api_url(docker_hostname, "users"),
            headers=req_headers(token=host_bb_token, content_type="application/json"),
            json_data=user_data,
            expected_statuses=(201,),
        )
        print(resp.json())
        response_user = resp.json()
        created_users.append(response_user)
        return user_data

    yield _make_host_user

    for user in created_users:
        print(f"Deleting user {user['name']!r} in source system...")
        http_request(
            "delete",
            bb_api_url(docker_hostname, "users", user["name"]),
            headers=req_headers(token=host_bb_token),
            expected_statuses=(204, 404),
        )


@pytest.fixture
def check_password(http_request):
    def _func(username: str, password: str, host: str):
        url = f"https://{host}/univention/auth/"
        http_request("get", url, params={"username": username, "password": password})

    return _func
