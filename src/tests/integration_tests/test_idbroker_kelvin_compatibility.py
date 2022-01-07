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
from ucsschool.kelvin.client import UserResource as KelvinUserResource

# load ID Broker plugin
ucsschool_id_connector.plugin_loader.load_plugins()
id_broker = pytest.importorskip("idbroker")
pytestmark = pytest.mark.id_broker

fake = faker.Faker()


@pytest.mark.asyncio
async def test_compatibilty_of_user_sync(
    wait_for_kelvin_object_exists,
    kelvin_session,
    id_connector_host_name,
    id_broker_ip,
    make_school_authority,
    id_broker_school_auth_conf,
    school_auth_config_kelvin,
    school_auth_host_configs,
    create_schools,
    make_sender_user,
    save_mapping,
):
    """
    tests if all users are replicated on the id broker and
    a subset is replicated on another school authority
    """
    target_ip = school_auth_host_configs["IP_traeger1"]
    other_school_authority = await make_school_authority(**school_auth_config_kelvin(2))
    broker_school_authority = await make_school_authority(
        plugin_name="id_broker", **id_broker_school_auth_conf
    )
    subprocess.Popen(["/etc/init.d/ucsschool-id-connector", "restart"])
    auth_school_mapping = await create_schools([(other_school_authority, 2)])
    ou_auth1 = auth_school_mapping[other_school_authority.name][0]
    mapping = {
        ou_auth1: other_school_authority.name,
    }
    await save_mapping(mapping)
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1])
    print(f"Created user {sender_user['name']!r} on sender")
    print(f"... looking for it in {other_school_authority.name}...")
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinUserResource,
        method="get",
        session=kelvin_session(target_ip),
        name=sender_user["name"],
    )
    print(f"... looking for it in {broker_school_authority.name}...")
    await wait_for_kelvin_object_exists(
        resource_cls=KelvinUserResource,
        method="get",
        session=kelvin_session(id_broker_ip),
        name=f"{broker_school_authority.name}-{sender_user['name']}",
        school=f"{broker_school_authority.name}-{sender_user['name']}",
    )
