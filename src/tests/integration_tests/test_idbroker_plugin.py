# -*- coding: utf-8 -*-

# Copyright 2021 Univention GmbH
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

import os
import random
import subprocess
from typing import List

import faker
import pytest

import ucsschool_id_connector.plugin_loader
from ucsschool.kelvin.client import (
    School as KelvinSchool,
    SchoolClass as KelvinSchoolClass,
    SchoolClassResource as KelvinSchoolClassResource,
    SchoolResource as KelvinSchoolResource,
    Session as KelvinSession,
    User as KelvinUser,
    UserResource as KelvinUserResource,
)
from ucsschool_id_connector.models import SchoolAuthorityConfiguration

# load ID Broker plugin
ucsschool_id_connector.plugin_loader.load_plugins()
id_broker = pytest.importorskip("idbroker")

fake = faker.Faker()


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("UNSAFE_SSL", "1")


@pytest.fixture(scope="session")
def id_connector_ip():
    return os.environ["nameserver1"]


@pytest.fixture(scope="session")
def get_local_kelvin_user():
    def _func(
        session: KelvinSession, school_name: str, classes: List[str], roles: List[str], s_a_name: str
    ) -> KelvinUser:
        return KelvinUser(
            name=f"{fake.user_name()}",
            school=f"{school_name}",
            firstname=fake.first_name(),
            lastname=fake.last_name(),
            disabled=False,
            record_uid=fake.uuid4(),
            roles=roles,
            schools=[f"{school_name}"],
            school_classes={f"{school_name}": classes},
            source_uid=f"IDBROKER-{s_a_name}",
            session=session,
        )

    return _func


@pytest.fixture(scope="session")
def get_local_kelvin_school_class():
    def _func(session: KelvinSession, school_name: str) -> KelvinSchoolClass:
        return KelvinSchoolClass(
            name=fake.user_name(),
            school=school_name,
            description=fake.first_name(),
            session=session,
            users=[],
        )

    return _func


@pytest.fixture(scope="function")
async def local_kelvin_school(kelvin_session, id_connector_ip):
    school = KelvinSchool(
        name=f"{fake.user_name()}",
        display_name=fake.first_name(),
        session=kelvin_session(id_connector_ip),
    )
    await school.save()
    return school


@pytest.fixture(scope="session")
async def new_school_auth(kelvin_session, id_broker_ip):
    """
    create a provisioning-admin user on the id broker system.
    """
    s_a_name = "".join(fake.street_name().split())
    print(f"*** Creating school authority {s_a_name!r}...")
    password = fake.password(length=15)
    kelvin_user = KelvinUser(
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
async def school_auth_conf(
    new_school_auth, school_auth_config_id_broker
) -> SchoolAuthorityConfiguration:
    s_a_name, password = new_school_auth
    return school_auth_config_id_broker(s_a_name, password)


# TODO cleanup schools, user & classes cf. test_id_broker_plugin.py
# This has to be done both on the ID-Connector & the ID Broker side.


@pytest.mark.asyncio
async def test_school_exists_after_user_with_non_existing_school_is_synced(
    local_kelvin_school,
    get_local_kelvin_user,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_ip,
    id_broker_ip,
    school_auth_conf,
    make_school_authority,
):
    """
    create kelvin user with non existing school
    -> school should be created on id-broker side
    -> the display_name should be set correct
    """

    school_authority = await make_school_authority(plugin_name="id_broker", **school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_user: KelvinUser = get_local_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_connector_ip),
        school_name=local_kelvin_school.name,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    await kelvin_user.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{kelvin_user.school}",
        display_name=local_kelvin_school.display_name,
    )


# IDBrokerPerSAGroupDispatcher


@pytest.mark.asyncio
async def test_school_exists_after_school_class_with_non_existin_school_is_synced(
    local_kelvin_school,
    get_local_kelvin_school_class,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_ip,
    id_broker_ip,
    make_school_authority,
    school_auth_conf,
):
    """
    create kelvin schoolclass with non existing school
    -> school should be created on id-broker side
        -> the display_name should be set correct
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_school_class: KelvinSchoolClass = get_local_kelvin_school_class(
        session=kelvin_session(id_connector_ip),
        school_name=local_kelvin_school.name,
    )
    await kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{kelvin_school_class.school}",
        display_name=local_kelvin_school.display_name,
    )


@pytest.mark.asyncio
async def test_handle_attr_description_empty(
    local_kelvin_school,
    get_local_kelvin_school_class,
    get_local_kelvin_user,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_ip,
    id_broker_ip,
    make_school_authority,
    school_auth_conf,
):
    """
    Creating a school class with an empty descritption should not
    lead to an error but set it to an empty string on the id-broker side.
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_school_class: KelvinSchoolClass = get_local_kelvin_school_class(
        session=kelvin_session(id_connector_ip),
        school_name=local_kelvin_school.name,
    )
    kelvin_school_class.description = None
    await kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=kelvin_school_class.name,
        school=f"{s_a_name}-{local_kelvin_school.name}",
        descritpion="",
    )


@pytest.mark.asyncio
async def test_handle_attr_users(
    local_kelvin_school,
    get_local_kelvin_school_class,
    get_local_kelvin_user,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_ip,
    id_broker_ip,
    make_school_authority,
    school_auth_conf,
):
    """
    Tests if the users of the kelvin class are placed inside on the
    id-broker side, see  IDBrokerPerSAGroupDispatcher._handle_attr_users

    This also tests implicitly
    - IDBrokerPerSAGroupDispatcher._handle_attr_name
    - IDBrokerPerSAGroupDispatcher._handle_attr_school
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    local_kelvin_user: KelvinUser = get_local_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_connector_ip),
        school_name=local_kelvin_school.name,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    await local_kelvin_user.save()
    local_kelvin_school_class: KelvinSchoolClass = get_local_kelvin_school_class(
        session=kelvin_session(id_connector_ip),
        school_name=local_kelvin_school.name,
    )
    local_kelvin_school_class.users = [local_kelvin_user.name]
    await local_kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=local_kelvin_school_class.name,
        school=f"{s_a_name}-{local_kelvin_school.name}",
        users=[f"{s_a_name}-{local_kelvin_user.name}"],
    )
    # test IDBrokerPerSAUserDispatcher._handle_attr_context
    remote_user: KelvinUserResource = await wait_for_kelvin_object_exists(
        resource_cls=KelvinUserResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{local_kelvin_user.name}",
        school=f"{s_a_name}-{local_kelvin_school.name}",
    )
    assert (
        local_kelvin_school_class.name
        in remote_user.school_classes[f"{s_a_name}-{local_kelvin_school.name}"]
    )
    assert set(local_kelvin_user.roles) == set(remote_user.roles)
