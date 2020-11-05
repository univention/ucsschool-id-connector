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

import asyncio
import datetime
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union
from urllib.parse import urljoin

import faker
import pytest
import requests
from pydantic import UrlStr
from urllib3.exceptions import InsecureRequestWarning

from ucsschool.kelvin.client import KelvinObject, KelvinResource, NoObject, Session
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
KELVIN_API_USERNAME = "Administrator"
KELVIN_API_PASSWORD = "univention"
KELVIN_API_CA_CERT_PATH = "/tmp/pytest_cacert_{date:%Y-%m-%d}_{host}.crt"


@pytest.fixture(scope="session")
def http_request():
    def _func(
        method: str,
        url: str,
        params: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        form_data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        verify: bool = False,
        expected_statuses: Iterable[int] = (200,),
        check_status: bool = True,
    ) -> requests.Response:
        req_meth = getattr(requests, method.lower())
        if not verify:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        response = req_meth(
            url,
            params=params,
            headers=headers,
            data=form_data,
            json=json_data,
            verify=verify,
        )
        try:
            msg = response.json()
        except JSONDecodeError:
            msg = "<no JSON>" if response.status_code in expected_statuses else response.text
        msg = (
            f"Status {response.status_code} (reason: {response.reason}) for "
            f"{method.upper()} {url!r} using headers={headers!r} and "
            f"json_data={json_data!r} -> msg: {msg}."
        )
        if check_status:
            assert response.status_code in expected_statuses, msg
        print(msg)
        return response

    return _func


@pytest.fixture(scope="session")
def school_auth_host_configs(docker_hostname: str, http_request):
    configs = {}
    for i in ("1", "2"):
        url = urljoin(f"https://{docker_hostname}", f"IP_traeger{i}.txt")
        resp = http_request("get", url, verify=False)
        assert resp.status_code == 200, (resp.status_code, resp.reason, url)
        configs["IP_traeger" + i] = resp.text.strip("\n")
    return configs


@pytest.fixture(scope="session")
def school_auth_config(docker_hostname: str, http_request, school_auth_host_configs):
    """
    Fixture to create configurations for school authorities. It expects a
    specific environment for the integration tests and can provide a maximum
    of two distinct configurations.
    """

    def _school_auth_config(auth_nr: int) -> Dict[str, str]:
        """
        Generates a configuration for a school authority.

        :param auth_nr: Request the config for either school authority auth1
            or school authority auth2
        :return: The school authority configuration in dictionary form
        """
        assert 0 < auth_nr < 3
        ip = school_auth_host_configs[f"IP_traeger{auth_nr}"]
        config = {
            "name": f"auth{auth_nr}",
            "active": True,
            "url": f"https://{ip}/ucsschool/kelvin/v1/",
            "plugins": ["kelvin"],
            "plugin_configs": {
                "kelvin": {
                    "mapping": {
                        "school_classes": {
                            "name": "name",
                            "description": "description",
                            "school": "school",
                            "users": "users",
                        },
                        "users": {
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
                    },
                    "password": "univention",
                    "passwords_target_attribute": "ucsschool_id_connector_pw",
                    "ssl_context": {
                        "check_hostname": False,
                    },
                    "username": "Administrator",
                },
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


@pytest.fixture(scope="session")
def url_fragment(docker_hostname):
    return f"http://{docker_hostname}/ucsschool/kelvin/v1"


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
        return urljoin(f"https://{docker_hostname}/{APP_ID}/api/v1/", f"{resource}/{entity}").rstrip("/")

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
def kelvin_auth_header(docker_hostname: str):
    url = f"http://{docker_hostname}/ucsschool/kelvin/token"
    print(url)
    response = requests.post(
        url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=dict(username="Administrator", password="univention"),
    )
    assert response.status_code == 200, f"{response.__dict__!r}"
    response_json = response.json()
    auth_header = {"Authorization": f"Bearer {response_json['access_token']}"}
    return auth_header


@pytest.fixture(scope="session")
def host_ucsschool_id_connector_token(docker_hostname: str, http_request) -> str:
    """
    Returns a valid token for the ucsschool-id-connector HTTP-API.
    """
    req_headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = http_request(
        "post",
        urljoin(f"https://{docker_hostname}", f"{APP_ID}/api/token"),
        verify=False,
        form_data=dict(username="Administrator", password="univention"),
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
    kelvin_school_authority_configuration,
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
        name: str,
        active: bool,
        url: UrlStr,
        plugins: List[str],
        plugin_configs: Dict[str, Dict[str, Any]],
    ) -> SchoolAuthorityConfiguration:
        """
        Creates and saves a school authority

        :param name: The school authorities name
        :param url: The url for the school authorities endpoint
        :param plugin_configs: configuration of plugins
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
        school_authority = kelvin_school_authority_configuration(
            name=name,
            active=active,
            url=url,
            plugins=plugins,
            plugin_configs=plugin_configs,
        )
        config_as_dict = school_authority.dict()
        config_as_dict["plugin_configs"]["kelvin"]["password"] = school_authority.plugin_configs[
            "kelvin"
        ]["password"].get_secret_value()
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
                and loaded_s_a.plugin_configs["kelvin"]["password"].get_secret_value()
                == plugin_configs["kelvin"]["password"]
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
                    f"SchoolAuthorityConfiguration(name={school_authority_name!r}) was not deleted."
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


def create_school(host: str, ou_name: str):
    print(f"Creating school {ou_name!r} on host {host!r}...")
    if not Path("/usr/bin/ssh").exists() or not Path("/usr/bin/sshpass").exists():
        subprocess.Popen(["apk", "add", "--no-cache", "openssh", "sshpass"], close_fds=True)
    print(f"ssh to {host} to create {ou_name} with /usr/share/ucs-school-import/scripts/create_ou")
    process = subprocess.Popen(
        [
            "sshpass",
            "-p",
            "univention",
            "ssh",
            "-o",
            "StrictHostKeyChecking no",
            f"root@{host}",
            "/usr/share/ucs-school-import/scripts/create_ou",
            ou_name,
        ],
        stderr=subprocess.PIPE,
        close_fds=True,
    )
    stdout, stderr = process.communicate()
    stderr = stderr.decode()
    assert (not stderr) or ("Already attached!" in stderr) or ("created successfully" in stderr)
    if "Already attached!" in stderr:
        print(f"OU {ou_name} exists in {host}.")


@pytest.fixture()
def create_schools(random_name):
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
            ous.extend(["testou-{}".format(random_name()) for i in range(amount - len(ous))])
            print(f"Creating OUs: {ous!r}...")
            for ou in ous:
                create_school(os.environ["nameserver1"], ou)

                print(f"Creating OU {ou!r} in {auth.name!r} ...")
                if ip := re.search(r"[\d+\.]+", auth.url).group():
                    create_school(ip, ou)

                if ou not in auth_school_mapping[auth.name]:
                    auth_school_mapping[auth.name].append(ou)
        with AUTH_SCHOOL_MAPPING_PATH.open("w") as fp:
            json.dump(auth_school_mapping, fp)
        return auth_school_mapping

    return _create_schools


@pytest.fixture()
async def make_sender_user(
    kelvin_auth_header,
    random_name,
    source_uid: str,
    url_fragment,
):
    """
    Fixture factory to create users on the apps host system. They are created
    via the Kelvin-API and automatically removed when the fixture goes out of scope.
    """
    created_users = list()

    def _make_sender_user(roles=("student",), ous=("DEMOSCHOOL",)):
        """
        Creates a user on the hosts UCS system via Kelvin-API

        :param roles: The new users roles
        :param ous: The new users ous
        :return: The json used to create the user via the API
        """
        firstname = fake.first_name()
        lastname = fake.last_name()
        user_data = dict(
            name=f"test.{firstname[:5]}.{lastname}"[:15],
            birthday=fake.date_of_birth(minimum_age=6, maximum_age=67).strftime("%Y-%m-%d"),
            disabled=False,
            firstname=firstname,
            lastname=lastname,
            password=fake.password(length=15),
            record_uid=f"{firstname[:5]}.{lastname}.{fake.pyint(1000, 9999)}",
            roles=[f"{url_fragment}/roles/{role}" for role in roles],
            school=f"{url_fragment}/schools/{ous[0]}",
            schools=[f"{url_fragment}/schools/{ou}" for ou in ous],
            school_classes={}
            if roles == ("staff",)
            else dict((ou, sorted([random_name(4), random_name(4)])) for ou in ous),
            source_uid=source_uid,
        )
        resp = requests.post(
            f"{url_fragment}/users/",
            headers={"Content-Type": "application/json", **kelvin_auth_header},
            data=json.dumps(user_data),
        )
        assert resp.status_code == 201, f"{resp.__dict__}"
        response_user = resp.json()
        created_users.append(response_user)
        return user_data

    yield _make_sender_user

    for user in created_users:
        print(f"Deleting user {user['name']!r} in source system...")
        response = requests.delete(f"{url_fragment}/users/{user['name']}", headers=kelvin_auth_header)
        assert response.status_code in (204, 404)


@pytest.fixture
def check_password(http_request):
    """Check authentication with `username` and `password` using UMC on `host`."""

    def _func(username: str, password: str, host: str) -> None:
        """May raise `AssertionError` if login check fails."""
        # url = f"https://{host}/univention/auth/"
        # http_request("get", url, params={"username": username, "password": password})
        # TODO: Kelvin API does not yet support password sync.
        print("===> NO PASSWORD CHECK PERFORMED (Kelvin API does not yet support it) <===")
        return

    return _func


@pytest.fixture(scope="session")
def ca_cert():
    """Downloaded CA certificate of UCS server `host`."""

    def _func(host: str) -> Path:
        path = Path(KELVIN_API_CA_CERT_PATH.format(date=datetime.date.today(), host=host))
        if not path.is_file():
            url = f"http://{host}/ucs-root-ca.crt"
            try:
                resp = requests.get(url)
            except requests.RequestException as exc:
                print(f"Error downloading CA from host {host!r}: {exc!s}")
                raise
            path.write_bytes(resp.content)
        return path

    return _func


@pytest.fixture(scope="session")
def kelvin_session_kwargs(ca_cert):
    """Dict to open a Kelvin API client session to `host`."""

    def is_ip(host: str) -> bool:
        for c in host:
            if c != "." and not c.isnumeric():
                return False
        return True

    def _func(host: str) -> Dict[str, Union[str, bool]]:
        res = {
            "username": KELVIN_API_USERNAME,
            "password": KELVIN_API_PASSWORD,
            "host": host,
            "verify": False if is_ip(host) else str(ca_cert(host)),
        }
        return res

    return _func


@pytest.fixture
async def kelvin_session(kelvin_session_kwargs):
    """
    An open Kelvin API client session to `host`, that will close automatically
    after the test.
    """
    sessions: Dict[str, Session] = {}

    def _func(host: str) -> Session:
        if host not in sessions:
            sessions[host] = Session(**kelvin_session_kwargs(host))
            sessions[host].open()
        return sessions[host]

    yield _func

    for session in sessions.values():
        await session.close()


@pytest.fixture(scope="session")
def wait_for_kelvin_object_exists():
    """
    Repeat executing `await resource_cls(session=session).method(**method_kwargs)`
    as long as `NoObject` is raised or until the timeout hits.
    """

    async def _func(
        resource_cls: Type[KelvinResource],
        method: str,
        session: Session,
        wait_timeout: int = 100,
        **method_kwargs,
    ) -> KelvinObject:
        end = datetime.datetime.now() + datetime.timedelta(seconds=wait_timeout)
        error: Optional[NoObject] = None
        while datetime.datetime.now() < end:
            resource = resource_cls(session=session)
            func = getattr(resource, method)
            try:
                return await func(**method_kwargs)
            except NoObject as exc:
                error = exc
                print(f"Waiting for {resource_cls.__name__}.{method}({method_kwargs!r}): {exc!s}")
                await asyncio.sleep(1)
        raise AssertionError(f"No object found after {wait_timeout} seconds: {error!s}")

    return _func


@pytest.fixture(scope="session")
def wait_for_kelvin_object_not_exists():
    """
    Repeat executing `await resource_cls(session=session).method(**method_kwargs)`
    until `NoObject` is raised or until the timeout hits.
    """

    async def _func(
        resource_cls: Type[KelvinResource],
        method: str,
        session: Session,
        wait_timeout: int = 100,
        **method_kwargs,
    ) -> None:
        end = datetime.datetime.now() + datetime.timedelta(seconds=wait_timeout)
        obj: Optional[KelvinObject] = None
        while datetime.datetime.now() < end:
            resource = resource_cls(session=session)
            func = getattr(resource, method)
            try:
                obj: KelvinObject = await func(**method_kwargs)
                print(f"Object {obj!r} still exists...")
                await asyncio.sleep(1)
            except NoObject:
                return
        raise AssertionError(f"Still finding {obj!r} after {wait_timeout} seconds.")

    return _func
