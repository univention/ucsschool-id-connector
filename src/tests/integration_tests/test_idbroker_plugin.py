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

import random
import subprocess
from typing import List

import faker
import pytest

import ucsschool_id_connector.plugin_loader
from ucsschool.kelvin.client import (
    SchoolClass as KelvinSchoolClass,
    SchoolClassResource as KelvinSchoolClassResource,
    SchoolResource as KelvinSchoolResource,
    Session as KelvinSession,
    User as KelvinUser,
    UserResource as KelvinUserResource,
)

# load ID Broker plugin
ucsschool_id_connector.plugin_loader.load_plugins()
id_broker = pytest.importorskip("idbroker")

fake = faker.Faker()


@pytest.fixture(scope="session")
def make_kelvin_user_on_sender():
    # todo use make_sender_user instead
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
def make_kelvin_school_class_on_sender():
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
async def kelvin_school_on_sender(create_school, id_connector_host_name):
    return await create_school(id_connector_host_name)


# TODO cleanup schools, user & classes cf. test_id_broker_plugin.py
# This has to be done both on the ID-Connector & the ID Broker side.


@pytest.mark.asyncio
async def test_school_exists_after_user_with_non_existing_school_is_synced(
    kelvin_school_on_sender,
    make_kelvin_user_on_sender,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    id_broker_school_auth_conf,
    make_school_authority,
):
    """
    create kelvin user with non existing school
    -> school should be created on id-broker side
    -> the display_name should be set correct
    """

    school_authority = await make_school_authority(plugin_name="id_broker", **id_broker_school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_user: KelvinUser = make_kelvin_user_on_sender(
        s_a_name=s_a_name,
        session=kelvin_session(id_connector_host_name),
        school_name=kelvin_school_on_sender.name,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    await kelvin_user.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{kelvin_user.school}",
        display_name=kelvin_school_on_sender.display_name,
    )


# IDBrokerPerSAGroupDispatcher


@pytest.mark.asyncio
async def test_school_exists_after_school_class_with_non_existin_school_is_synced(
    kelvin_school_on_sender,
    make_kelvin_school_class_on_sender,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    make_school_authority,
    id_broker_school_auth_conf,
):
    """
    create kelvin schoolclass with non existing school
    -> school should be created on id-broker side
    -> the display_name should be set correct
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **id_broker_school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_school_class: KelvinSchoolClass = make_kelvin_school_class_on_sender(
        session=kelvin_session(id_connector_host_name),
        school_name=kelvin_school_on_sender.name,
    )
    await kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{kelvin_school_class.school}",
        display_name=kelvin_school_on_sender.display_name,
    )


@pytest.mark.asyncio
async def test_handle_attr_description_empty(
    kelvin_school_on_sender,
    make_kelvin_school_class_on_sender,
    make_kelvin_user_on_sender,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    make_school_authority,
    id_broker_school_auth_conf,
):
    """
    Creating a school class with an empty descritption should not
    lead to an error but set it to an empty string on the id-broker side.
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **id_broker_school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    kelvin_school_class: KelvinSchoolClass = make_kelvin_school_class_on_sender(
        session=kelvin_session(id_connector_host_name),
        school_name=kelvin_school_on_sender.name,
    )
    kelvin_school_class.description = None
    await kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=kelvin_school_class.name,
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
        descritpion="",
    )


@pytest.mark.asyncio
async def test_handle_attr_users(
    kelvin_school_on_sender,
    make_kelvin_school_class_on_sender,
    make_kelvin_user_on_sender,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    make_school_authority,
    id_broker_school_auth_conf,
):
    """
    Tests if the users of the kelvin class are placed inside on the
    id-broker side, see  IDBrokerPerSAGroupDispatcher._handle_attr_users

    This also tests implicitly
    - IDBrokerPerSAGroupDispatcher._handle_attr_name
    - IDBrokerPerSAGroupDispatcher._handle_attr_school
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **id_broker_school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    local_kelvin_user: KelvinUser = make_kelvin_user_on_sender(
        s_a_name=s_a_name,
        session=kelvin_session(id_connector_host_name),
        school_name=kelvin_school_on_sender.name,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    await local_kelvin_user.save()
    local_kelvin_school_class: KelvinSchoolClass = make_kelvin_school_class_on_sender(
        session=kelvin_session(id_connector_host_name),
        school_name=kelvin_school_on_sender.name,
    )
    local_kelvin_school_class.users = [local_kelvin_user.name]
    await local_kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=local_kelvin_school_class.name,
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
        users=[f"{s_a_name}-{local_kelvin_user.name}"],
    )
    # test IDBrokerPerSAUserDispatcher._handle_attr_context
    remote_user: KelvinUserResource = await wait_for_kelvin_object_exists(
        resource_cls=KelvinUserResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{local_kelvin_user.name}",
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
    )
    assert (
        local_kelvin_school_class.name
        in remote_user.school_classes[f"{s_a_name}-{kelvin_school_on_sender.name}"]
    )
    assert set(local_kelvin_user.roles) == set(remote_user.roles)
