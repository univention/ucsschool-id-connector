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
from typing import List

import faker
import pytest

import ucsschool_id_connector.plugin_loader
from ucsschool.kelvin.client import (
    School as KelvinSchool,
    SchoolResource as KelvinSchoolResource,
    User as KelvinUser,
    UserResource as KelvinUserResource,
)
from ucsschool_id_connector.models import SchoolAuthorityConfiguration

# load ID Broker plugin
ucsschool_id_connector.plugin_loader.load_plugins()
id_broker = pytest.importorskip("idbroker")
from idbroker.id_broker_client import IDBrokerUser, SchoolContext, User  # isort:skip  # noqa: E402

fake = faker.Faker()


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("UNSAFE_SSL", "1")


@pytest.fixture
async def school_auth_conf(school_auth_config_id_broker) -> SchoolAuthorityConfiguration:
    sac = school_auth_config_id_broker("Berlin")
    return SchoolAuthorityConfiguration(**sac)


@pytest.fixture
def get_schools(id_broker_ip, kelvin_session):
    async def _func(s_a_name: str) -> List[KelvinSchool]:
        return [
            school
            async for school in KelvinSchoolResource(session=kelvin_session(id_broker_ip)).search(
                name=f"{s_a_name}-*"
            )
        ]

    return _func


@pytest.fixture
def test_school(get_schools):
    async def _func(s_a_name: str) -> KelvinSchool:
        res = random.choice(await get_schools(s_a_name))
        assert res, "TODO: create school if none exists"
        return res

    return _func


@pytest.fixture
def test_school_name(test_school):
    async def _func(s_a_name: str) -> str:
        return (await test_school(s_a_name)).name.split("-", 1)[-1]

    return _func


@pytest.fixture
def test_user():
    async def _func(school_name: str, classes: List[str], roles: List[str]) -> User:
        return User(
            id=fake.uuid4(),
            user_name=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            context={school_name: SchoolContext(classes=classes, roles=roles)},
        )

    return _func


@pytest.fixture
def get_kelvin_user(id_broker_ip, kelvin_session):
    async def _func(s_a_name: str, user_name: str) -> KelvinUser:
        return await KelvinUserResource(session=kelvin_session(id_broker_ip)).get(
            name=f"{s_a_name}-{user_name}"
        )

    return _func


@pytest.fixture
def compare_kelvin_and_id_broker_user():
    def _func(kelvin_user: KelvinUser, id_broker_user: User, s_a_name: str):
        assert kelvin_user.record_uid == id_broker_user.id
        assert kelvin_user.firstname == id_broker_user.first_name
        assert kelvin_user.lastname == id_broker_user.last_name
        assert kelvin_user.name == f"{s_a_name}-{id_broker_user.user_name}"
        for school, school_context in id_broker_user.context.items():
            idb_school = f"{s_a_name}-{school}"
            assert idb_school in kelvin_user.schools
            assert {f"{role}:school:{idb_school}" for role in school_context.roles}.issubset(
                set(kelvin_user.ucsschool_roles)
            )
            if school_context.classes:
                assert idb_school in kelvin_user.school_classes
                assert set(school_context.classes) == set(kelvin_user.school_classes[idb_school])

    return _func


@pytest.mark.asyncio
async def test_user_create(
    compare_kelvin_and_id_broker_user,
    get_kelvin_user,
    mock_env,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_school_name,
    test_user,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    user_1: User = await test_user(school_name=school, classes=["1a"], roles=["student"])
    user_2: User = await id_broker_user.create(user_1)
    assert user_1 == user_2
    kelvin_user = await get_kelvin_user(s_a_name, user_1.user_name)
    compare_kelvin_and_id_broker_user(kelvin_user, user_2, s_a_name)
