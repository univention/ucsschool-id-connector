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
from idbroker.id_broker_client import (  # isort:skip  # noqa: E402
    IDBrokerSchool,
    IDBrokerSchoolClass,
    IDBrokerUser,
    School,
    SchoolContext,
    SchoolClass,
    User,
)

fake = faker.Faker()


@pytest.fixture(scope="session")
async def new_school_auth(delete_kelvin_school, kelvin_session, id_broker_ip) -> Tuple[str, str]:
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

    await delete_kelvin_school(s_a_name, school_name)
    try:
        await kelvin_user.delete()
        print(f"Deleted user {kelvin_user.name!r}.")
    except KelvinNoObject:
        print(f"User {kelvin_user.name!r} does not exist.")


@pytest.fixture(scope="session")
async def school_auth_conf(
    school_auth_config_id_broker, new_id_broker_school_auth
) -> SchoolAuthorityConfiguration:
    s_a_name, password = new_id_broker_school_auth
    sac = school_auth_config_id_broker(s_a_name, password)
    return SchoolAuthorityConfiguration(**sac)


@pytest.fixture(scope="session")
def get_schools(school_auth_conf, id_broker_kelvin_session):
    """
    searches for schools on the id-broker system
    if no school is found, a new one is created.
    """

    async def _get_schools(s_a_name: str) -> List[KelvinSchool]:
        return [
            school
            async for school in KelvinSchoolResource(
                session=id_broker_kelvin_session(school_auth_conf)
            ).search(name=f"{s_a_name}-*")
        ]

    async def _func(s_a_name: str) -> List[KelvinSchool]:
        schools_on_s_a = await _get_schools(s_a_name)
        if not schools_on_s_a:
            school_name = fake.user_name()
            id_broker_school = IDBrokerSchool(school_auth_conf, "id_broker")
            school_1 = School(name=school_name, display_name=f"{s_a_name} {school_name}")
            await id_broker_school.create(school_1)
            return await _get_schools(s_a_name)
        return schools_on_s_a

    return _func


@pytest.fixture(scope="session")
def test_school_name(get_schools):
    async def _func(s_a_name: str) -> str:
        test_school = random.choice(await get_schools(s_a_name))
        return test_school.name.split("-", 1)[-1]

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


@pytest.fixture(scope="session")
def get_kelvin_school_class(id_broker_ip, kelvin_session):
    async def _func(s_a_name: str, class_name: str, school_name: str) -> KelvinSchoolClass:
        return await KelvinSchoolClassResource(session=kelvin_session(id_broker_ip)).get(
            name=class_name, school=f"{s_a_name}-{school_name}"
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


def compare_kelvin_and_id_broker_school(
    kelvin_school: KelvinSchool, id_broker_school: School, s_a_name: str
):
    assert kelvin_school.name == f"{s_a_name}-{id_broker_school.name}"
    assert kelvin_school.display_name == id_broker_school.display_name


@pytest.fixture
def compare_kelvin_and_id_broker_school_class(get_kelvin_user):
    async def _func(kelvin_class: KelvinSchoolClass, id_broker_class: SchoolClass, s_a_name: str):
        assert kelvin_class.name == id_broker_class.name
        assert kelvin_class.description == id_broker_class.description
        assert kelvin_class.school == f"{s_a_name}-{id_broker_class.school}"
        kelvin_users: List[KelvinUser] = [
            await get_kelvin_user(s_a_name, username) for username in kelvin_class.users
        ]
        assert set(u.record_uid for u in kelvin_users) == set(id_broker_class.members)

    return _func


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


@pytest.fixture(scope="session")
def delete_kelvin_school(kelvin_session, id_broker_ip):
    async def _func(s_a_name: str, name: str) -> None:
        session = kelvin_session(id_broker_ip)
        schools = [
            school
            async for school in KelvinSchoolResource(session=session).search(name=f"{s_a_name}-{name}")
        ]
        if not schools:
            print(f"*** delete_kelvin_school(): no such school: '{s_a_name}-{name}'.")
            return
        school_dn = schools[0].dn
        res_del = httpx.delete(
            f"https://Administrator:univention@{session.host}/univention/udm/container/ou/{school_dn}",
            verify=False,
        )
        if res_del.status_code not in (200, 204):
            print(f"*** Error deleting OU {schools[0].name!r}. ***")
        else:
            print(f"Deleted school {schools[0].name!r}.")

    return _func


@pytest.fixture
async def schedule_delete_kelvin_school(
    delete_kelvin_school, school_auth_conf, id_broker_kelvin_session
):
    s_a_and_school_names: List[Tuple[str, str]] = []

    def _func(s_a_name: str, name: str):
        s_a_and_school_names.append((s_a_name, name))

    yield _func

    for s_a_name, name in s_a_and_school_names:
        print(f"Deleting Kelvin school {name!r} (auth: {s_a_name!r})...")
        await delete_kelvin_school(s_a_name, name)


@pytest.fixture
async def schedule_delete_kelvin_school_class(get_kelvin_school_class):
    s_a_and_sc_names: List[Tuple[str, str, str]] = []

    def _func(s_a_name: str, name: str, school: str):
        s_a_and_sc_names.append((s_a_name, name, school))

    yield _func

    for s_a_name, name, school in s_a_and_sc_names:
        print(f"Deleting Kelvin school class {name!r} at school {school!r} (auth: {s_a_name!r})...")
        try:
            kelvin_class: KelvinSchoolClass = await get_kelvin_school_class(s_a_name, name, school)
            await kelvin_class.delete()
        except KelvinNoObject:
            print(
                f"Kelvin school class {name!r} at school {school!r} (auth: {s_a_name!r}) does not "
                f"exist."
            )


@pytest.mark.asyncio
async def test_school_create(
    get_schools,
    mock_env,
    schedule_delete_kelvin_school,
    school_auth_conf: SchoolAuthorityConfiguration,
):
    id_broker_school = IDBrokerSchool(school_auth_conf, "id_broker")
    s_a_name = id_broker_school.school_authority_name
    school_name = fake.user_name()
    school_1 = School(name=school_name, display_name=f"{s_a_name} {school_name}")
    schedule_delete_kelvin_school(s_a_name, school_name)
    school_2 = await id_broker_school.create(school_1)
    assert school_1 == school_2
    s_a_schools: List[KelvinSchool] = await get_schools(s_a_name)
    kelvin_school_name = f"{s_a_name}-{school_name}"
    assert kelvin_school_name in {school.name for school in s_a_schools}
    kelvin_school = [school for school in s_a_schools if school.name == kelvin_school_name][0]
    compare_kelvin_and_id_broker_school(kelvin_school, school_2, s_a_name)


@pytest.mark.asyncio
async def test_school_exists(
    get_schools,
    mock_env,
    school_auth_conf: SchoolAuthorityConfiguration,
):
    id_broker_school = IDBrokerSchool(school_auth_conf, "id_broker")
    s_a_name = id_broker_school.school_authority_name
    s_a_schools: List[KelvinSchool] = await get_schools(s_a_name)
    kelvin_school = random.choice(s_a_schools)
    res = await id_broker_school.exists(kelvin_school.name.split("-", 1)[-1])
    assert res is True
    res = await id_broker_school.exists(fake.user_name())
    assert res is False


@pytest.mark.asyncio
async def test_school_get(
    get_schools,
    mock_env,
    school_auth_conf: SchoolAuthorityConfiguration,
):
    id_broker_school = IDBrokerSchool(school_auth_conf, "id_broker")
    s_a_name = id_broker_school.school_authority_name
    s_a_schools: List[KelvinSchool] = await get_schools(s_a_name)
    kelvin_school = random.choice(s_a_schools)
    school = await id_broker_school.get(kelvin_school.name.split("-", 1)[-1])
    compare_kelvin_and_id_broker_school(kelvin_school, school, s_a_name)


@pytest.mark.asyncio
async def test_school_class_create(
    compare_kelvin_and_id_broker_school_class,
    get_kelvin_school_class,
    id_broker_ip,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_sc = IDBrokerSchoolClass(school_auth_conf, "id_broker")
    s_a_name = id_broker_sc.school_authority_name
    class_name = fake.user_name()
    school: str = await test_school_name(s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    sc_1 = SchoolClass(
        name=class_name,
        description=f"desc {s_a_name} {class_name}",
        school=school,
        members=[kelvin_user.record_uid],
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
    sc_2 = await id_broker_sc.create(sc_1)
    assert sc_1 == sc_2
    kelvin_class: KelvinSchoolClass = await get_kelvin_school_class(s_a_name, class_name, school)
    compare_kelvin_and_id_broker_school_class(kelvin_class, sc_2, s_a_name)


@pytest.mark.asyncio
async def test_school_class_exists(
    id_broker_ip,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_school_name,
):
    id_broker_sc = IDBrokerSchoolClass(school_auth_conf, "id_broker")
    s_a_name = id_broker_sc.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_sc = KelvinSchoolClass(
        name=fake.user_name(),
        school=f"{s_a_name}-{school}",
        users=[],
        session=kelvin_session(id_broker_ip),
    )
    res = await id_broker_sc.exists(kelvin_sc.name, school)
    assert res is False
    schedule_delete_kelvin_school_class(s_a_name, kelvin_sc.name, school)
    await kelvin_sc.save()
    res = await id_broker_sc.exists(kelvin_sc.name, school)
    assert res is True


@pytest.mark.asyncio
async def test_school_class_get(
    compare_kelvin_and_id_broker_school_class,
    id_broker_ip,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_school_name,
):
    id_broker_sc = IDBrokerSchoolClass(school_auth_conf, "id_broker")
    s_a_name = id_broker_sc.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_sc = KelvinSchoolClass(
        name=fake.user_name(),
        school=f"{s_a_name}-{school}",
        users=[],
        session=kelvin_session(id_broker_ip),
    )
    schedule_delete_kelvin_school_class(s_a_name, kelvin_sc.name, school)
    await kelvin_sc.save()
    sc: SchoolClass = await id_broker_sc.get(kelvin_sc.name, school)
    compare_kelvin_and_id_broker_school_class(kelvin_sc, sc, s_a_name)


@pytest.mark.asyncio
async def test_school_class_update(
    compare_kelvin_and_id_broker_school_class,
    get_kelvin_school_class,
    id_broker_ip,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_sc = IDBrokerSchoolClass(school_auth_conf, "id_broker")
    s_a_name = id_broker_sc.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_sc_1 = KelvinSchoolClass(
        name=fake.user_name(),
        school=f"{s_a_name}-{school}",
        users=[],
        session=kelvin_session(id_broker_ip),
    )
    schedule_delete_kelvin_school_class(s_a_name, kelvin_sc_1.name, school)
    await kelvin_sc_1.save()
    sc_1: SchoolClass = await id_broker_sc.get(kelvin_sc_1.name, school)
    compare_kelvin_and_id_broker_school_class(kelvin_sc_1, sc_1, s_a_name)
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    sc_1.description = fake.last_name()
    sc_1.members.clear()
    sc_1.members.append(kelvin_user.record_uid)
    sc_2: SchoolClass = await id_broker_sc.update(sc_1)
    sc_3: SchoolClass = await id_broker_sc.get(kelvin_sc_1.name, school)
    assert sc_2 == sc_3
    assert sc_1 == sc_2
    kelvin_sc_2: KelvinSchoolClass = await get_kelvin_school_class(s_a_name, kelvin_sc_1.name, school)
    compare_kelvin_and_id_broker_school_class(kelvin_sc_2, sc_3, s_a_name)


@pytest.mark.asyncio
async def test_school_class_delete(
    id_broker_ip,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_school_name,
    compare_kelvin_and_id_broker_school_class,
    get_kelvin_school_class,
):
    id_broker_sc = IDBrokerSchoolClass(school_auth_conf, "id_broker")
    s_a_name = id_broker_sc.school_authority_name
    school: str = await test_school_name(s_a_name)
    kelvin_sc = KelvinSchoolClass(
        name=fake.user_name(),
        school=f"{s_a_name}-{school}",
        users=[],
        session=kelvin_session(id_broker_ip),
    )
    schedule_delete_kelvin_school_class(s_a_name, kelvin_sc.name, school)
    await kelvin_sc.save()
    sc: SchoolClass = await id_broker_sc.get(kelvin_sc.name, school)
    compare_kelvin_and_id_broker_school_class(kelvin_sc, sc, s_a_name)
    await id_broker_sc.delete(sc.name, school)
    with pytest.raises(KelvinNoObject):
        await get_kelvin_school_class(s_a_name, sc.name, school)


@pytest.mark.asyncio
async def test_user_create(
    get_kelvin_user,
    mock_env,
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_id_broker_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    user_1: User = await test_id_broker_user(
        school_name=school, classes=[class_name], roles=[random.choice(("student", "teacher"))]
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
    schedule_delete_kelvin_user(s_a_name, user_1.user_name.split("-", 1)[-1])
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
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[class_name],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
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
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=id_broker_kelvin_session(school_auth_conf),
        school_name=school,
        classes=[class_name],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
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
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[class_name],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    user: User = await id_broker_user.get(kelvin_user.record_uid)
    compare_kelvin_and_id_broker_user(kelvin_user, user, s_a_name)


@pytest.mark.asyncio
async def test_user_update(
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[class_name],
        roles=[random.choice(("student", "teacher"))],
    )
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
    schedule_delete_kelvin_user(s_a_name, kelvin_user.name.split("-", 1)[-1])
    await kelvin_user.save()
    orig_id_broker_user: User = await id_broker_user.get(kelvin_user.record_uid)
    compare_kelvin_and_id_broker_user(kelvin_user, orig_id_broker_user, s_a_name)
    orig_id_broker_user.first_name = fake.first_name()
    orig_id_broker_user.last_name = fake.last_name()
    for school, context in orig_id_broker_user.context.items():
        context.classes.clear()
        context.classes.extend(["2b", "1a"])
    updated_id_broker_user: User = await id_broker_user.update(orig_id_broker_user)
    get_updated_id_broker_user: User = await id_broker_user.get(orig_id_broker_user.id)
    assert updated_id_broker_user == get_updated_id_broker_user
    orig_user_classes = [
        (school, set(context.classes)) for school, context in orig_id_broker_user.context.items()
    ]
    updated_user_classes = [
        (school, set(context.classes)) for school, context in updated_id_broker_user.context.items()
    ]
    assert orig_user_classes == updated_user_classes


@pytest.mark.asyncio
async def test_user_update_change_username(
    get_kelvin_user,
    id_broker_ip: str,
    kelvin_session,
    mock_env,
    schedule_delete_kelvin_school_class,
    schedule_delete_kelvin_user,
    school_auth_conf: SchoolAuthorityConfiguration,
    test_kelvin_user,
    test_school_name,
):
    id_broker_user = IDBrokerUser(school_auth_conf, "id_broker")
    s_a_name = id_broker_user.school_authority_name
    school: str = await test_school_name(s_a_name)
    class_name = fake.user_name()
    kelvin_user: KelvinUser = test_kelvin_user(
        s_a_name=s_a_name,
        session=kelvin_session(id_broker_ip),
        school_name=school,
        classes=[class_name],
        roles=[random.choice(("student", "teacher"))],
    )
    old_user_name = kelvin_user.name.split("-", 1)[-1]
    schedule_delete_kelvin_school_class(s_a_name, class_name, school)
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
