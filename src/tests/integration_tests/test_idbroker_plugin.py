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

import subprocess
from typing import Any, Dict

import faker
import pytest

import ucsschool_id_connector.plugin_loader
from ucsschool.kelvin.client import (
    SchoolClass as KelvinSchoolClass,
    SchoolClassResource as KelvinSchoolClassResource,
    SchoolResource as KelvinSchoolResource,
    UserResource as KelvinUserResource,
)

# load ID Broker plugin
ucsschool_id_connector.plugin_loader.load_plugins()
id_broker = pytest.importorskip("idbroker")
pytestmark = pytest.mark.id_broker

fake = faker.Faker()

# TODO cleanup schools has to be done both on the ID-Connector & the ID Broker side.
# Users & classes are cleaned up implicitly when they are deleted on
# the ID Connector side.


@pytest.mark.asyncio
async def test_school_exists_after_user_with_non_existing_school_is_synced(
    kelvin_school_on_sender,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    id_broker_school_auth_conf,
    make_school_authority,
    make_sender_user,
):
    """
    create kelvin user with non existing school
    -> school should be created on id-broker side
    -> the display_name should be set correct
    """
    school_authority = await make_school_authority(plugin_name="id_broker", **id_broker_school_auth_conf)
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    s_a_name = school_authority.name
    sender_user: Dict[str, Any] = await make_sender_user(ous=[kelvin_school_on_sender.name])
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{sender_user['school']}",
        display_name=kelvin_school_on_sender.display_name,
    )


# IDBrokerPerSAGroupDispatcher


@pytest.mark.asyncio
async def test_school_exists_after_school_class_with_non_existin_school_is_synced(
    kelvin_school_on_sender,
    make_kelvin_school_class,
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
    sender_kelvin_school_class: KelvinSchoolClass = await make_kelvin_school_class(
        school_name=kelvin_school_on_sender.name,
        sa_name=s_a_name,
        host=id_connector_host_name,
    )
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{sender_kelvin_school_class.school}",
        display_name=kelvin_school_on_sender.display_name,
    )


@pytest.mark.asyncio
async def test_school_class_handle_attr_description_empty(
    kelvin_school_on_sender,
    make_kelvin_school_class,
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
    sender_kelvin_school_class: KelvinSchoolClass = await make_kelvin_school_class(
        school_name=kelvin_school_on_sender.name,
        sa_name=s_a_name,
        host=id_connector_host_name,
    )
    sender_kelvin_school_class.description = None
    await sender_kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=sender_kelvin_school_class.name,
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
        descritpion="",
    )


@pytest.mark.asyncio
async def test_handle_attr_users(
    kelvin_school_on_sender,
    make_kelvin_school_class,
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    make_school_authority,
    id_broker_school_auth_conf,
    make_sender_user,
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
    sender_user: Dict[str, Any] = await make_sender_user(ous=[kelvin_school_on_sender.name])
    sender_kelvin_school_class: KelvinSchoolClass = await make_kelvin_school_class(
        school_name=kelvin_school_on_sender.name,
        sa_name=s_a_name,
        host=id_connector_host_name,
    )
    sender_kelvin_school_class.users = [sender_user["name"]]
    await sender_kelvin_school_class.save()
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinSchoolClassResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=sender_kelvin_school_class.name,
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
        users=[f"{s_a_name}-{sender_user['name']}"],
    )
    # test IDBrokerPerSAUserDispatcher._handle_attr_context
    remote_user: KelvinUserResource = await wait_for_kelvin_object_exists(
        resource_cls=KelvinUserResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{s_a_name}-{sender_user['name']}",
        school=f"{s_a_name}-{kelvin_school_on_sender.name}",
    )
    assert (
        sender_kelvin_school_class.name
        in remote_user.school_classes[f"{s_a_name}-{kelvin_school_on_sender.name}"]
    )
    assert set(sender_user["roles"]) == set(remote_user.roles)
