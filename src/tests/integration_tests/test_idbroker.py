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
import zlib
from typing import List, Tuple

import faker
import httpx
import pytest

import ucsschool_id_connector.plugin_loader
from ucsschool.kelvin.client import (
    NoObject as KelvinNoObject,
    School as KelvinSchool,
    SchoolResource as KelvinSchoolResource,
    Session as KelvinSession,
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


@pytest.fixture(scope="session")
async def new_school_auth(kelvin_session, id_broker_ip) -> Tuple[str, str]:
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
        roles=["staff"],
        schools=["DEMOSCHOOL"],
        session=kelvin_session(id_broker_ip),
    )
    await kelvin_user.save()
    print(f"Created admin user {kelvin_user.name!r}.")
    school_name = fake.user_name()
    # TODO: impl. save() for kelvin.client SchoolResource (only for create, not update)
    session = kelvin_session(id_broker_ip)
    kelvin_school = KelvinSchool(
        name=f"{s_a_name}-{school_name}",
        display_name=f"{s_a_name} {school_name}",
        educational_servers=[f"{zlib.crc32(s_a_name.encode())}-dc"],  # crc32 > 10 ints > total: 13 chars
        session=kelvin_session(id_broker_ip),
    )
    data = kelvin_school._to_kelvin_request_data()
    data = {k: v for k, v in data.items() if v is not None}
    res_post = await session.post(session.urls["school"], json=data)
    print(f"Created school {res_post['name']!r}.")

    yield s_a_name, password

    res_del = httpx.delete(
        f"https://Administrator:univention@{session.host}/univention/udm/container/ou/{res_post['dn']}",
        verify=False,
    )
    if res_del.status_code not in (200, 204):
        print(f"*** Error deleting OU {res_post['name']!r}. ***")
    else:
        print(f"Deleted school {res_post['name']!r}.")
    try:
        await kelvin_user.delete()
        print(f"Deleted user {kelvin_user.name!r}.")
    except KelvinNoObject:
        print(f"User {kelvin_user.name!r} does not exist.")


@pytest.fixture(scope="session")
async def school_auth_conf(
    school_auth_config_id_broker, new_school_auth
) -> SchoolAuthorityConfiguration:
    s_a_name, password = new_school_auth
    sac = school_auth_config_id_broker(s_a_name, password)
    return SchoolAuthorityConfiguration(**sac)


@pytest.fixture(scope="session")
def get_schools(school_auth_conf, id_broker_kelvin_session):
    async def _func(s_a_name: str) -> List[KelvinSchool]:
        return [
            school
            async for school in KelvinSchoolResource(
                session=id_broker_kelvin_session(school_auth_conf)
            ).search(name=f"{s_a_name}-*")
        ]

    return _func


@pytest.fixture(scope="session")
def test_school(get_schools):
    async def _func(s_a_name: str) -> KelvinSchool:
        res = random.choice(await get_schools(s_a_name))
        assert res, "TODO: create school if none exists"
        return res

    return _func


@pytest.fixture(scope="session")
def test_school_name(test_school):
    async def _func(s_a_name: str) -> str:
        return (await test_school(s_a_name)).name.split("-", 1)[-1]

    return _func


@pytest.fixture(scope="session")
def test_id_broker_user():
    async def _func(school_name: str, classes: List[str], roles: List[str]) -> User:
        return User(
            id=fake.uuid4(),
            user_name=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            context={school_name: SchoolContext(classes=classes, roles=roles)},
        )

    return _func


@pytest.fixture(scope="session")
def test_kelvin_user():
    def _func(
        s_a_name: str, session: KelvinSession, school_name: str, classes: List[str], roles: List[str]
    ) -> KelvinUser:
        return KelvinUser(
            name=f"{s_a_name}-{fake.user_name()}",
            school=f"{s_a_name}-{school_name}",
            firstname=fake.first_name(),
            lastname=fake.last_name(),
            disabled=False,
            record_uid=fake.uuid4(),
            roles=roles,
            schools=[f"{s_a_name}-{school_name}"],
            school_classes={f"{s_a_name}-{school_name}": classes},
            source_uid=f"IDBROKER-{s_a_name}",
            session=session,
        )

    return _func


@pytest.fixture(scope="session")
def get_kelvin_user(id_broker_ip, kelvin_session):
    async def _func(s_a_name: str, user_name: str) -> KelvinUser:
        return await KelvinUserResource(session=kelvin_session(id_broker_ip)).get(
            name=f"{s_a_name}-{user_name}"
        )

    return _func


def compare_kelvin_and_id_broker_user(kelvin_user: KelvinUser, id_broker_user: User, s_a_name: str):
    assert kelvin_user.record_uid == id_broker_user.id
    assert kelvin_user.source_uid == f"IDBROKER-{s_a_name}"
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


@pytest.fixture
async def schedule_delete_kelvin_user(get_kelvin_user):
    s_a_and_user_names: List[Tuple[str, str]] = []

    def _func(s_a_name: str, user_name: str):
        s_a_and_user_names.append((s_a_name, user_name))

    yield _func

    for s_a_and_user_name in s_a_and_user_names:
        print(f"Deleting Kelvin user '{s_a_and_user_name[0]}-{s_a_and_user_name[1]}'...")
        try:
            kelvin_user: KelvinUser = await get_kelvin_user(*s_a_and_user_name)
            await kelvin_user.delete()
        except KelvinNoObject:
            print(f"Kelvin user '{s_a_and_user_name[0]}-{s_a_and_user_name[1]}' does not exist.")


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_create():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_exists():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_get():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_class_create():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_class_exists():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_class_get():
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="TODO")
async def test_school_class_update():
    ...


@pytest.mark.asyncio
async def test_user_create(
    get_kelvin_user,
    mock_env,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_id_broker_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    user_1: User = await test_id_broker_user(
        school_name=school, classes=["1a"], roles=[random.choice(("student", "teacher"))]
    )
    schedule_delete_kelvin_user(s_a_name, user_1.user_name)
    user_2: User = await id_broker_user.create(user_1)
    assert user_1 == user_2
    kelvin_user = await get_kelvin_user(s_a_name, user_1.user_name)
    compare_kelvin_and_id_broker_user(kelvin_user, user_2, s_a_name)


@pytest.mark.asyncio
async def test_user_delete(
    get_kelvin_user,
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=["1a"],
        roles=[random.choice(("student", "teacher"))],
    )
    await kelvin_user.save()
    user: User = await id_broker_user.get(kelvin_user.record_uid)
    await id_broker_user.delete(user.id)
    with pytest.raises(KelvinNoObject):
        await get_kelvin_user(s_a_name, user.user_name)


@pytest.mark.asyncio
async def test_user_exists(
    id_broker_ip: str,
    id_broker_kelvin_session,
    mock_env,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=id_broker_kelvin_session(school_auth_conf),
        school_name=school,
        classes=["1a"],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    exists = await id_broker_user.exists(kelvin_user.record_uid)
    assert exists is True
    await id_broker_user.delete(kelvin_user.record_uid)
    exists = await id_broker_user.exists(kelvin_user.record_uid)
    assert exists is False


@pytest.mark.asyncio
async def test_user_get(
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=["1a"],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    user: User = await id_broker_user.get(kelvin_user.record_uid)
    compare_kelvin_and_id_broker_user(kelvin_user, user, s_a_name)


@pytest.mark.asyncio
async def test_user_update(
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=["1a"],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    user_1: User = await id_broker_user.get(kelvin_user.record_uid)
    compare_kelvin_and_id_broker_user(kelvin_user, user_1, s_a_name)
    user_1.first_name = fake.first_name()
    user_1.last_name = fake.last_name()
    for school, context in user_1.context.items():
        context.classes.clear()
        context.classes.extend(["1a", "2b"])
    user_2: User = await id_broker_user.update(user_1)
    user_3: User = await id_broker_user.get(user_1.id)
    assert user_2 == user_3
    assert user_1 == user_2


@pytest.mark.asyncio
async def test_user_update_change_username(
    get_kelvin_user,
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=["1a"],
        roles=[random.choice(("student", "teacher"))],
    )
    old_user_name = kelvin_user.name.split("-", 1)[-1]
    schedule_delete_kelvin_user(s_a_name, old_user_name)
    await kelvin_user.save()
    user_1: User = await id_broker_user.get(kelvin_user.record_uid)
    compare_kelvin_and_id_broker_user(kelvin_user, user_1, s_a_name)
    user_1.user_name = fake.user_name()
    assert old_user_name != user_1.user_name
    schedule_delete_kelvin_user(s_a_name, user_1.user_name)
    user_2: User = await id_broker_user.update(user_1)
    user_3: User = await id_broker_user.get(user_1.id)
    assert user_2 == user_3
    assert user_1 == user_2
    assert user_3.user_name != old_user_name
    with pytest.raises(KelvinNoObject):
        await get_kelvin_user(s_a_name, old_user_name)
    kelvin_user_2 = await get_kelvin_user(s_a_name, user_3.user_name)
    assert kelvin_user_2.name == f"{s_a_name}-{user_3.user_name}"
