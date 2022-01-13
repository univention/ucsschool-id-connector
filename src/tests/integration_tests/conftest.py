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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union
from urllib.parse import urljoin

import faker
import pytest
import requests
from pydantic import UrlStr
from urllib3.exceptions import InsecureRequestWarning

from ucsschool.kelvin.client import (
    InvalidRequest,
    KelvinObject,
    KelvinResource,
    NoObject,
    School,
    SchoolClass,
    SchoolClassResource,
    Session,
    User,
    UserResource,
)
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
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
def school_auth_host_configs(docker_hostname: str, http_request) -> Dict[str, str]:
    configs = {}
    for i in ("1", "2"):
        url = urljoin(f"https://{docker_hostname}", f"IP_traeger{i}.txt")
        resp = http_request("get", url, verify=False)
        assert resp.status_code == 200, (resp.status_code, resp.reason, url)
        configs[f"IP_traeger{i}"] = resp.text.strip("\n")
        resp = http_request(
            "get",
            f"https://Administrator:univention@{configs[f'IP_traeger{i}']}"
            f"/univention/udm/ldap/base/",
            headers={"Accept": "application/json"},
            verify=False,
        )
        resp_json = resp.json()
        configs[f"base_dn_traeger{i}"] = resp_json["dn"]
        resp = http_request(
            "get",
            f"https://Administrator:univention@{configs[f'IP_traeger{i}']}"
            f"/univention/udm/users/user/?query[username]=Administrator",
            headers={"Accept": "application/json"},
            verify=False,
        )
        resp_json = resp.json()
        configs[f"administrator_dn_traeger{i}"] = resp_json["_embedded"]["udm:object"][0]["dn"]
    print(f"school_auth_host_configs: {configs!r}")
    return configs


@pytest.fixture(scope="session")
def school_auth_config_kelvin(docker_hostname: str, http_request, school_auth_host_configs):
    """
    Fixture to create configurations for school authorities using Kelvin.
    It expects a specific environment for the integration tests and can provide a maximum
    of two distinct configurations.
    """

    def _school_auth_config_kelvin(auth_nr: int) -> Dict[str, Any]:
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
                            "userexpiry": "expiration_date",
                            "phone": "phone",
                            "ucsschoolRecordUID": "record_uid",
                        },
                    },
                    "password": "univention",
                    "sync_password_hashes": True,
                    "ssl_context": {
                        "check_hostname": False,
                    },
                    "username": "Administrator",
                },
            },
        }
        return config

    yield _school_auth_config_kelvin


@pytest.fixture(scope="session")
def id_broker_ip(docker_hostname: str, http_request) -> str:
    url = urljoin(f"https://{docker_hostname}", "IP_idbroker.txt")
    resp = http_request("get", url, verify=False)
    assert resp.status_code == 200, (resp.status_code, resp.reason, url)
    return resp.text.strip()


@pytest.fixture(scope="session")
def id_connector_host_name(docker_hostname):
    return docker_hostname


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("UNSAFE_SSL", "1")


@pytest.fixture(scope="session")
def school_auth_config_id_broker(id_broker_ip):
    """
    Fixture to create configurations for replicating to the ID Broker.
    """

    def _school_auth_config_id_broker(s_a_name: str, password: str) -> Dict[str, Any]:
        """
        Generates a configuration for a school authority.

        :return: The school authority configuration in dictionary form
        """
        return {
            "name": s_a_name,
            "active": True,
            "url": f"https://{id_broker_ip}/",
            "plugins": ["id_broker-users", "id_broker-groups"],
            "plugin_configs": {
                "id_broker": {
                    "password": password,
                    "username": f"provisioning-{s_a_name}",
                    "version": 1,
                },
            },
        }

    return _school_auth_config_id_broker


@pytest.fixture(scope="session")
async def new_id_broker_school_auth(kelvin_session, id_broker_ip):
    """
    create a provisioning-admin user on the id broker system.
    """
    s_a_name = "".join(fake.street_name().split())
    print(f"*** Creating school authority {s_a_name!r}...")
    password = fake.password(length=15)
    kelvin_user = User(
        name=f"provisioning-{s_a_name}",
        school="DEMOSCHOOL",
        firstname=fake.first_name(),
        lastname=fake.last_name(),
        disabled=False,
        password=password,
        record_uid=fake.uuid4(),
        roles=["teacher"],
        schools=["DEMOSCHOOL"],
        session=kelvin_session(id_broker_ip),
    )
    await kelvin_user.save()
    print(f"Created admin user {kelvin_user.name!r}.")

    yield s_a_name, password


@pytest.fixture(scope="session")
async def id_broker_school_auth_conf(
    new_id_broker_school_auth, school_auth_config_id_broker
) -> SchoolAuthorityConfiguration:
    s_a_name, password = new_id_broker_school_auth
    return school_auth_config_id_broker(s_a_name, password)


@pytest.fixture()
def req_headers():
    """
    Fixture to create request headers for ucsschool-id-connector-API requests.
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
def source_uid() -> str:
    """
    The source UID as specified in the ucsschool-id-connector App settings.
    """
    return get_ucrv(f"{APP_ID}/source_uid")


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
        name: str,
        active: bool,
        url: UrlStr,
        plugins: List[str],
        plugin_configs: Dict[str, Dict[str, Any]],
        plugin_name: str = "kelvin",
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
        school_authority = school_authority_configuration(
            name=name,
            active=active,
            url=url,
            plugins=plugins,
            plugin_configs=plugin_configs,
        )
        config_as_dict = school_authority.dict()
        config_as_dict["plugin_configs"][plugin_name]["password"] = school_authority.plugin_configs[
            plugin_name
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
                and loaded_s_a.plugin_configs[plugin_name]["password"].get_secret_value()
                == plugin_configs[plugin_name]["password"]
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


@pytest.fixture(scope="session")
async def create_school(kelvin_session):
    async def _func(host: str, ou_name: str = ""):
        if not ou_name:
            ou_name = f"{fake.user_name()[:10]}"
        school = School(
            name=ou_name,
            display_name=fake.first_name(),
            session=kelvin_session(host),
        )

        try:
            school = await school.save()
            print(f" => OU {ou_name!r} created in {host!r}.")
        except InvalidRequest:
            print(f" => OU {ou_name!r} exists in {host!r}.")

        return school

    return _func


@pytest.fixture(scope="function")
async def kelvin_school_on_sender(create_school, id_connector_host_name):
    return await create_school(id_connector_host_name)


@pytest.fixture()
def create_schools(docker_hostname, random_name, create_school):
    """
    Fixture factory to create OUs. The OUs are cached during multiple test runs
    to save development time.
    """
    if AUTH_SCHOOL_MAPPING_PATH.exists():
        with AUTH_SCHOOL_MAPPING_PATH.open("r") as fp:
            auth_school_mapping = json.load(fp)
    else:
        auth_school_mapping = dict()

    async def _create_schools(
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
            ous.extend(["ou-{}".format(random_name())[:10] for _ in range(amount - len(ous))])
            print(f"Creating OUs: {ous!r}...")
            for ou in ous:
                hosts = [docker_hostname]
                if ip := re.search(r"[\d+\.]+", auth.url).group():
                    hosts.append(ip)
                for ip in hosts:
                    await create_school(host=ip, ou_name=ou)
                if ou not in auth_school_mapping[auth.name]:
                    auth_school_mapping[auth.name].append(ou)
        with AUTH_SCHOOL_MAPPING_PATH.open("w") as fp:
            json.dump(auth_school_mapping, fp)
        return auth_school_mapping

    return _create_schools


@pytest.fixture()
async def make_sender_user(
    random_name,
    source_uid: str,
    kelvin_session,
    kelvin_session_kwargs,
    docker_hostname,
    school_auth_host_configs,
):
    """
    Fixture factory to create users on the apps host system. They are created
    via the Kelvin-API and automatically removed when the fixture goes out of scope.
    """
    created_users: List[Dict[str, Any]] = []

    async def _make_sender_user(roles=("student",), ous=("DEMOSCHOOL",)):
        """
        Creates a user on the hosts UCS system via Kelvin-API-Client

        :param roles: The new users roles
        :param ous: The new users ous
        :return: The json used to create the user via the API
        """
        firstname = fake.first_name()
        lastname = fake.last_name()
        user_obj = User(
            name=f"test.{firstname[:5]}.{lastname}"[:15],
            birthday=fake.date_of_birth(minimum_age=6, maximum_age=67),
            disabled=False,
            firstname=firstname,
            lastname=lastname,
            password=fake.password(length=15),
            record_uid=f"{firstname[:5]}.{lastname}.{fake.pyint(1000, 9999)}",
            roles=roles,
            school=ous[0],
            schools=ous,
            school_classes={}
            if roles == ("staff",)
            else dict((ou, sorted([random_name(4), random_name(4)])) for ou in ous),
            source_uid=source_uid,
            session=kelvin_session(docker_hostname),
        )
        password = user_obj.password
        await user_obj.save()
        user_obj.password = password
        user_obj_as_dict = user_obj.as_dict()
        created_users.append(user_obj_as_dict)
        print("Created new User in source system: {!r}".format(user_obj_as_dict))
        return user_obj_as_dict

    yield _make_sender_user

    for host in (
        docker_hostname,
        school_auth_host_configs["IP_traeger1"],
        school_auth_host_configs["IP_traeger2"],
    ):
        for user_dict in created_users:
            print(f"Deleting user {user_dict['name']!r} from host {host!r}...")
            # Creating a new session per user deletion, because of a problem in httpx/httpcore/h11.
            # I think it has a problem with the disconnect happening by Kelvin with FastAPI delete():
            # h11._util.LocalProtocolError: Too much data for declared Content-Length
            async with Session(**kelvin_session_kwargs(host)) as session:
                try:
                    user = await UserResource(session=session).get(name=user_dict["name"])
                    await user.delete()
                    print(f"Success deleting user {user_dict['name']!r} from host {host!r}.")
                except NoObject:
                    print(f"No user {user_dict['name']!r} on {host!r}.")


@pytest.fixture
def check_password(http_request):
    """Check authentication with `username` and `password` using UMC on `host`."""

    def _func(username: str, password: str, host: str) -> None:
        """May raise `AssertionError` if login check fails."""
        print(f"Password check: username={username!r} password={password!r} host={host!r}...")
        resp = http_request(
            "post",
            f"https://{host}/univention/auth/",
            params={"username": username, "password": password},
            expected_statuses=(200,),
        )
        json_resp = resp.json()
        assert json_resp["status"] == 200

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
        return {
            "username": KELVIN_API_USERNAME,
            "password": KELVIN_API_PASSWORD,
            "host": host,
            "verify": False if is_ip(host) else str(ca_cert(host)),
        }

    return _func


@pytest.fixture(scope="session")
async def kelvin_session(kelvin_session_kwargs):
    """
    An open Kelvin API client session to `host`, that will close automatically
    after the test.
    """
    sessions: Dict[str, Session] = {}

    def _func(host: str, **kwargs) -> Session:
        if host not in sessions:
            session_kwargs = kelvin_session_kwargs(host)
            session_kwargs.update(kwargs)
            sessions[host] = Session(**session_kwargs)
            sessions[host].open()
        return sessions[host]

    yield _func

    for session in sessions.values():
        await session.close()


@pytest.fixture(scope="session")
def id_broker_kelvin_session(kelvin_session):
    def _func(sac: SchoolAuthorityConfiguration) -> Session:
        m = re.match(r"^https://(?P<host>.+?)/", sac.url)
        assert m
        host = m.groupdict()["host"]
        username = sac.plugin_configs["id_broker"]["username"]
        password = sac.plugin_configs["id_broker"]["password"].get_secret_value()
        return kelvin_session(host=host, username=username, password=password)

    return _func


@pytest.fixture()
async def make_kelvin_school_class(kelvin_session, id_connector_host_name, id_broker_ip):
    created_school_classes: List[Tuple[str]] = []

    async def _func(school_name: str, sa_name: str, host: str) -> SchoolClass:
        sc_obj = SchoolClass(
            name=fake.user_name(),
            school=school_name,
            description=fake.first_name(),
            session=kelvin_session(id_connector_host_name),
            users=[],
        )
        await sc_obj.save()
        created_school_classes.append((id_connector_host_name, sc_obj.name, sc_obj.school))
        return sc_obj

    yield _func

    for host, name, school in created_school_classes:
        try:
            _sc = await SchoolClassResource(session=kelvin_session(host)).get(name=name, school=school)
            await _sc.delete()
            print(f"Success deleting school class {name!r} from host {host!r}.")
        except NoObject:
            print(f"No school class {name!r} on {host!r}.")


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
