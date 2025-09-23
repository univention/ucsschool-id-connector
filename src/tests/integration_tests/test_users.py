# -*- coding: utf-8 -*-

# Copyright 2019-2023 Univention GmbH
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
import copy
import glob
import json
import subprocess
import time
import traceback
from typing import Any, Dict, Iterable
from urllib.parse import urlsplit

import faker
import pytest
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from ucsschool.kelvin.client import NoObject, Session, User, UserResource
from ucsschool_id_connector.ldap_access import LDAPAccess

try:
    from simplejson.errors import JSONDecodeError
except ImportError:  # pragma: no cover
    JSONDecodeError = ValueError

fake = faker.Faker()
# This is not a performance test, so we chose I long interval.
WAIT_FOR_REPLICATION_TIMEOUT = 600.0


@pytest.fixture(scope="session")
def compare_user(compare_dicts):
    def _func(source: Dict[str, Any], other: Dict[str, Any], to_check: Iterable[str] = None):
        """
        This function compares two dictionaries. Specifically it checks if all
        key-value pairs from the source also exist in the other dictionary. It
        does not assert all key-value pairs from the other dictionary to be in the
        source!

        :param source: The original dictionary
        :param other: The dictionary to check against the original source
        :param to_check: The keys to check.
        """
        to_check = to_check or (
            "name",
            "firstname",
            "lastname",
            "birthday",
            "expiration_date",
            "disabled",
            "record_uid",
            "school_classes",
            "source_uid",
        )
        return compare_dicts(source, other, to_check)

    return _func


def filter_ous(user: Dict[str, Any], auth: str, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Remove OUs from `users` 'schools' and 'school_classes' attributes,
    that belong to auth other than `auth`.
    """
    result_user = copy.deepcopy(user)
    _mapping = {k.lower(): v for k, v in mapping.items()}
    for school_url in user["schools"]:
        school = school_url.rstrip("/").split("/")[-1]
        if _mapping[school.lower()] != auth:
            result_user["schools"].remove(school_url)
    for class_ou in user["school_classes"].keys():
        if _mapping[class_ou.lower()] != auth:
            del result_user["school_classes"][class_ou]
    return result_user


@pytest.fixture(scope="session")
def assert_equal_password_hashes(school_auth_host_configs):
    async def _func(username: str, host1: str, host2: str) -> None:
        print(f"Comparing password hashes of user {username!r} on host {host1!r} and {host2!r}...")
        ldap_access1 = LDAPAccess(host=host1, ldap_base=school_auth_host_configs["base_dn_traeger1"])
        ldap_access2 = LDAPAccess(host=host2, ldap_base=school_auth_host_configs["base_dn_traeger2"])
        timeout = 300
        remaining_time = timeout

        # sambaPwdLastSet may need a few seconds to sync
        while True:
            hashes1 = await ldap_access1.get_passwords(
                username,
                base=school_auth_host_configs["base_dn_traeger1"],
                bind_dn=school_auth_host_configs["administrator_dn_traeger1"],
                bind_pw="univention",
            )
            hashes2 = await ldap_access2.get_passwords(
                username,
                base=school_auth_host_configs["base_dn_traeger2"],
                bind_dn=school_auth_host_configs["administrator_dn_traeger2"],
                bind_pw="univention",
            )

            if hashes1 == hashes2:
                break
            elif remaining_time <= 0:
                break

            await asyncio.sleep(1)
            remaining_time -= 1

        assert hashes1 == hashes2

    return _func


@pytest.mark.asyncio
@pytest.mark.parametrize("roles", [("student",), ("teacher",), ("legal_guardian",)])
@pytest.mark.parametrize("ou_case_correct", (True, False))
async def test_create_user(
    make_school_authority,
    make_sender_user,
    school_auth_config_kelvin,
    save_mapping,
    create_schools,
    docker_hostname,
    check_password,
    compare_user,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
    assert_equal_password_hashes,
    scramble_case,
    ou_case_correct: bool,
    roles,
):
    """
    Tests if ucsschool_id_connector distributes a newly created User to the correct school
    authorities.
    """
    target_1 = school_auth_host_configs["traeger1"]
    target_2 = school_auth_host_configs["traeger2"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    school_auth2 = await make_school_authority(**school_auth_config_kelvin(2))
    auth_school_mapping = await create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = ou_auth1_original = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = ou_auth1_2_original = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = ou_auth2_original = auth_school_mapping[school_auth2.name][0]
    if not ou_case_correct:
        print("===> Wrong OU case!")
        ou_auth1 = scramble_case(ou_auth1_original)
        assert ou_auth1 != ou_auth1_original
        print(f"===> original: {ou_auth1_original!r} scrambled: {ou_auth1!r}")
        ou_auth1_2 = scramble_case(ou_auth1_2_original)
        assert ou_auth1_2 != ou_auth1_2_original
        print(f"===> original: {ou_auth1_2_original!r} -> scrambled: {ou_auth1_2!r}")
        ou_auth2 = scramble_case(ou_auth2_original)
        assert ou_auth2 != ou_auth2_original
        print(f"===> original: {ou_auth2_original!r} -> scrambled: {ou_auth2!r}")
    mapping = {
        ou_auth1: school_auth1.name,
        ou_auth1_2: school_auth1.name,
        ou_auth2: school_auth2.name,
    }
    await save_mapping(mapping)
    print(f"===> Mapping: {mapping!r}")
    print(f"===> ou_auth1  : OU {ou_auth1!r} @ auth {school_auth1.name!r}")
    print(f"===> ou_auth1_2: OU {ou_auth1_2!r} @ auth {school_auth1.name!r}")
    print(f"===> ou_auth2  : OU {ou_auth2!r} @ auth {school_auth2.name!r}")
    for num, ous in enumerate(((ou_auth1,), (ou_auth1, ou_auth1_2), (ou_auth1, ou_auth2)), start=1):
        print(f"===> Case {num}/3: Creating user on sender in ous={ous!r}...")
        sender_user: Dict[str, Any] = await make_sender_user(roles=roles, ous=ous)
        # verify user on sender system
        await UserResource(session=kelvin_session(docker_hostname)).get(name=sender_user["name"])
        # check_password(sender_user["name"], sender_user["password"], docker_hostname)
        print(f"Created user {sender_user['name']!r} on sender, looking for it in auth1...")
        existence_test_task = wait_for_kelvin_object_exists(
            resource_cls=UserResource,
            method="get",
            session=kelvin_session(target_1),
            name=sender_user["name"],
            wait_timeout=60,
        )
        if "legal_guardian" in roles:
            with pytest.raises(AssertionError, match="No object.*"):
                user_remote: User = await existence_test_task
            continue
        user_remote: User = await existence_test_task
        print(f"Found {user_remote!r}, checking its attributes...")
        expected_target_user1 = filter_ous(sender_user, school_auth1.name, mapping)
        compare_user(expected_target_user1, user_remote.as_dict())
        check_password(
            sender_user["name"],
            sender_user["password"],
            urlsplit(school_auth1.url).netloc,
        )
        await assert_equal_password_hashes(sender_user["name"], docker_hostname, target_1)
        if ou_auth2 in ous:
            print(f"User should also be in OU2 ({ou_auth2!r}), checking...")
            user_remote: User = await wait_for_kelvin_object_exists(
                resource_cls=UserResource,
                method="get",
                session=kelvin_session(target_2),
                name=sender_user["name"],
            )
            expected_target_user2 = filter_ous(sender_user, school_auth2.name, mapping)
            compare_user(expected_target_user2, user_remote.as_dict())
            check_password(
                sender_user["name"],
                sender_user["password"],
                urlsplit(school_auth2.url).netloc,
            )
            await assert_equal_password_hashes(sender_user["name"], docker_hostname, target_2)
        else:
            print(f"User should NOT be in OU2 ({ou_auth2!r}), checking...")
            with pytest.raises(NoObject):
                await UserResource(session=kelvin_session(target_2)).get(name=sender_user["name"])


@pytest.mark.asyncio
@pytest.mark.skip(
    "Disabled due to the new base image and move away from processes within containers. "
    "Further work is tracked in https://forge.univention.org/bugzilla/show_bug.cgi?id=57372"
)
async def test_move_to_trash_if_plugin_error_is_raised(
    make_school_authority,
    make_sender_user,
    school_auth_config_kelvin,
    save_mapping,
    create_schools,
):
    conf = school_auth_config_kelvin(auth_nr=1)
    # this will raise a KeyError in users_kelvin.py
    conf["plugin_configs"]["kelvin"]["mapping"].pop("users")
    school_auth1 = await make_school_authority(**conf, restart_id_connector_after_deletion=True)
    subprocess.check_call(["/etc/init.d/ucsschool-id-connector", "restart"])
    auth_school_mapping = await create_schools(
        [
            (school_auth1, 2),
        ]
    )
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    mapping = {
        ou_auth1: school_auth1.name,
    }
    await save_mapping(mapping)
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1])
    trash_dir = (
        f"/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/"
        f"out_queues/{school_auth1.name}/trash"
    )
    found = False
    for attempt in Retrying(
        wait=wait_fixed(5), stop=stop_after_attempt(3), retry=retry_if_exception_type(AssertionError)
    ):
        with attempt:
            for filename in glob.glob(rf"{trash_dir}/*.json"):
                with open(filename) as fin:
                    data = json.load(fin)
                    if data.get("object").get("username") == sender_user["name"]:
                        found = True
                        break
            assert found, f"File was not moved to {trash_dir}"


@pytest.mark.asyncio
async def test_delete_user(
    make_school_authority,
    make_sender_user,
    school_auth_config_kelvin,
    save_mapping,
    create_schools,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
    wait_for_kelvin_object_not_exists,
    docker_hostname,
):
    """
    Tests if ucsschool_id_connector distributes the deletion of an existing
    user correctly.
    """
    target_1 = school_auth_host_configs["traeger1"]
    target_2 = school_auth_host_configs["traeger2"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    school_auth2 = await make_school_authority(**school_auth_config_kelvin(2))
    auth_school_mapping = await create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
    mapping = {
        ou_auth1: school_auth1.name,
        ou_auth1_2: school_auth1.name,
        ou_auth2: school_auth2.name,
    }
    await save_mapping(mapping)
    print(f"Mapping: {mapping!r}")
    sender_user: Dict[str, Any] = await make_sender_user(ous=(ou_auth1, ou_auth2))
    print(f"Created user {sender_user['name']!r} in sender. Looking for it now in auth1...")
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    print(f"Found user {sender_user['name']!r} in ou_auth1. Looking for it now in auth2...")
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_2),
        name=sender_user["name"],
    )
    print(f"Deleting user {sender_user['name']!r} in sender...")
    user = await UserResource(session=kelvin_session(docker_hostname)).get(name=sender_user["name"])
    await user.delete()
    print(
        f"User {sender_user['name']!r} was deleted in sender, waiting for it to "
        f"disappear in ou_auth1..."
    )
    await wait_for_kelvin_object_not_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    print(
        f"User {sender_user['name']!r} disappeared in ou_auth1, waiting for it to "
        f"also disappear in ou_auth2..."
    )
    await wait_for_kelvin_object_not_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_2),
        name=sender_user["name"],
    )


async def change_properties(session: Session, username: str, changes: Dict[str, Any]) -> User:
    user: User = await UserResource(session=session).get(name=username)
    for property, value in changes.items():
        if property == "udm_properties":
            for udm_property, udm_value in value.items():
                user.udm_properties[udm_property] = udm_value
        assert hasattr(user, property)
        setattr(user, property, value)
    return await user.save()


@pytest.mark.asyncio
@pytest.mark.not_44_compatible
async def test_modify_user(
    make_school_authority,
    make_sender_user,
    school_auth_config_kelvin,
    save_mapping,
    create_schools,
    docker_hostname,
    check_password,
    compare_user,
    compare_dicts,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
    assert_equal_password_hashes,
):
    """
    Tests if the modification of a user is properly distributed to the school
    authority
    """
    target_1 = school_auth_host_configs["traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    school_auth2 = await make_school_authority(**school_auth_config_kelvin(2))
    auth_school_mapping = await create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
    await save_mapping(
        {
            ou_auth1: school_auth1.name,
            ou_auth1_2: school_auth1.name,
            ou_auth2: school_auth2.name,
        }
    )
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1])
    # check user exists on sender
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(docker_hostname),
        name=sender_user["name"],
    )
    check_password(sender_user["name"], sender_user["password"], docker_hostname)
    # check user exists on auth1
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    check_password(sender_user["name"], sender_user["password"], target_1)
    await assert_equal_password_hashes(sender_user["name"], docker_hostname, target_1)
    # Modify user
    new_password = fake.password(length=15)
    new_value = {
        "firstname": fake.first_name(),
        "lastname": fake.last_name(),
        "disabled": not sender_user["disabled"],
        "birthday": fake.date_of_birth(minimum_age=6, maximum_age=67),
        "expiration_date": fake.date_between(start_date="+1y", end_date="+10y"),
        "password": new_password,
        "udm_properties": {
            "pwdChangeNextLogin": not sender_user["udm_properties"]["pwdChangeNextLogin"],
            "title": fake.first_name(),
        },
    }
    await change_properties(kelvin_session(docker_hostname), sender_user["name"], new_value)
    user_on_host: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )

    # compare without password and udm properties
    del new_value["password"]
    keys_to_check = set(new_value.keys())
    keys_to_check.remove("udm_properties")
    compare_dicts(new_value, user_on_host.as_dict(), keys_to_check)

    # compare udm_properties
    udm_keys_to_check = new_value["udm_properties"].keys()
    compare_dicts(
        new_value["udm_properties"], user_on_host.as_dict()["udm_properties"], udm_keys_to_check
    )
    # Check if user was modified on target host
    timeout = 300
    while timeout > 0:
        await asyncio.sleep(5)
        timeout -= 5
        remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
            name=sender_user["name"]
        )
        if remote_user.firstname == new_value["firstname"]:
            break
    else:
        print(f"Waited {timeout}s without the user changing its firstname, continuing...")

    remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
        name=sender_user["name"]
    )

    compare_user(user_on_host.as_dict(), remote_user.as_dict())

    # jkoeniger/22.02.2023: Check also keys from keys_to_check and udm_properties
    compare_dicts(user_on_host.as_dict(), remote_user.as_dict(), keys_to_check)
    compare_dicts(
        user_on_host.as_dict()["udm_properties"],
        remote_user.as_dict()["udm_properties"],
        udm_keys_to_check,
    )

    # we need to enable the user and allow login via the old password before the check
    # changing pwdChangeNextLogin back to False/0 also sets sambaPwdLastSet
    await change_properties(
        kelvin_session(docker_hostname),
        sender_user["name"],
        {"disabled": False, "udm_properties": {"pwdChangeNextLogin": False}},
    )

    print("Checking password change...")
    check_password(sender_user["name"], new_password, docker_hostname)

    # same for the remote user1
    remote_user.disabled = False
    remote_user.udm_properties["pwdChangeNextLogin"] = False

    await remote_user.save()
    check_password(sender_user["name"], new_password, target_1)

    await assert_equal_password_hashes(sender_user["name"], docker_hostname, target_1)


def _check_schools_and_classes(user_kelvin, new_school, new_schools, new_school_classes):
    assert user_kelvin.school == new_school
    assert set(user_kelvin.schools) == new_schools
    assert user_kelvin.school_classes == new_school_classes


@pytest.mark.asyncio
async def test_class_change(
    make_school_authority,
    school_auth_config_kelvin,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
):
    """
    Tests if the modification of a users class is properly distributed by
    ucsschool-id-connector.
    """
    target_1 = school_auth_host_configs["traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    auth_school_mapping = await create_schools([(school_auth1, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    await save_mapping({ou_auth1: school_auth1.name})
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1])
    sender_user_kelvin: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    assert sender_user_kelvin.school_classes == sender_user["school_classes"]
    print(
        f"1. Created user {sender_user['name']} with school_classes="
        f"{sender_user['school_classes']!r} on sender."
    )
    user_auth1: User = await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    assert user_auth1.school_classes == sender_user["school_classes"]
    print(f"2. User was created in auth1 with school_classes={user_auth1.school_classes!r}.")
    new_value = {"school_classes": {ou_auth1: [random_name()]}}
    print(f"3. setting new value for school_classes on sender: {new_value!r}")
    await change_properties(kelvin_session(docker_hostname), sender_user["name"], new_value)
    user_on_host: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    school_classes_at_sender = user_on_host.school_classes
    assert school_classes_at_sender == new_value["school_classes"]
    sender_user_kelvin: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    assert sender_user_kelvin.school_classes == new_value["school_classes"]
    print(f"4. User was modified at sender, has now school_classes={school_classes_at_sender!r}.")
    # Check if user was modified on target host
    start = time.time()
    remote_user = None
    while not remote_user:
        remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
            name=sender_user["name"]
        )
        try:
            _check_schools_and_classes(
                remote_user,
                sender_user_kelvin.school,
                new_schools={sender_user_kelvin.school},
                new_school_classes=new_value["school_classes"],
            )
        except AssertionError:
            time_taken = time.time() - start
            assert (
                time_taken < WAIT_FOR_REPLICATION_TIMEOUT
            ), f"took more than {WAIT_FOR_REPLICATION_TIMEOUT}s: {traceback.format_exc()}"


@pytest.mark.asyncio
async def test_school_change(
    make_school_authority,
    school_auth_config_kelvin,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
):
    """
    Tests if the modification of a users school is properly distributed by
    ucsschool-id-connector.
    """
    target_1 = school_auth_host_configs["traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    auth_school_mapping = await create_schools([(school_auth1, 2)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    await save_mapping({ou_auth1: school_auth1.name, ou_auth1_2: school_auth1.name})
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1])
    print(
        f"Created user {sender_user['name']} with school={sender_user['school']!r} and "
        f"and schools={sender_user['schools']!r} on sender."
    )
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    new_school = ou_auth1_2
    new_value = {
        "school_classes": {new_school: [random_name()]},
        "school": new_school,
        "schools": [new_school],
    }

    print(f"Changing user on sender: {new_value!r}")
    await change_properties(kelvin_session(docker_hostname), sender_user["name"], new_value)
    sender_user_kelvin = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    print(
        f"User was modified at sender, has now school={sender_user_kelvin.school!r} "
        f"schools={sender_user_kelvin.schools!r} "
        f"school_classes={sender_user_kelvin.school_classes!r}."
    )

    _check_schools_and_classes(
        sender_user_kelvin,
        new_school,
        new_schools={new_school},
        new_school_classes=new_value["school_classes"],
    )
    start = time.time()
    remote_user = None
    while not remote_user:
        remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
            name=sender_user["name"]
        )
        try:
            _check_schools_and_classes(
                remote_user,
                new_school,
                new_schools={new_school},
                new_school_classes=new_value["school_classes"],
            )
        except AssertionError:
            time_taken = time.time() - start
            assert (
                time_taken < WAIT_FOR_REPLICATION_TIMEOUT
            ), f"took more than {WAIT_FOR_REPLICATION_TIMEOUT}s: {traceback.format_exc()}"


@pytest.mark.parametrize("role", ["student", "teacher"])
@pytest.mark.asyncio
async def test_change_school_and_schools(
    make_school_authority,
    school_auth_config_kelvin,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
    role,
):
    """
    Tests if the modifications of a users school + schools are properly distributed by
    ucsschool-id-connector. (Bug 54411)
    """
    target_1 = school_auth_host_configs["traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    auth_school_mapping = await create_schools([(school_auth1, 3)])
    ou_auth1_1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth1_3 = auth_school_mapping[school_auth1.name][2]
    await save_mapping(
        {ou_auth1_1: school_auth1.name, ou_auth1_2: school_auth1.name, ou_auth1_3: school_auth1.name}
    )
    sender_user: Dict[str, Any] = await make_sender_user(roles=(role,), ous=[ou_auth1_1, ou_auth1_2])
    print(
        f"Created user {sender_user['name']} with school={sender_user['school']!r} and "
        f"and schools={sender_user['schools']!r} on sender."
    )
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    new_prim_school = ou_auth1_2
    new_add_school = ou_auth1_3
    new_value = {
        "school_classes": {new_prim_school: [random_name()], new_add_school: [random_name()]},
        "school": new_prim_school,
        "schools": [new_prim_school, new_add_school],
    }

    print(f"Changing user on sender: {new_value!r}")
    await change_properties(kelvin_session(docker_hostname), sender_user["name"], new_value)
    sender_user_kelvin = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    print(
        f"User was modified at sender, has now school={sender_user_kelvin.school!r} "
        f"schools={sender_user_kelvin.schools!r} "
        f"school_classes={sender_user_kelvin.school_classes!r}."
    )

    _check_schools_and_classes(
        sender_user_kelvin,
        new_prim_school,
        new_schools={new_prim_school, new_add_school},
        new_school_classes=new_value["school_classes"],
    )
    start = time.time()
    remote_user = None
    while not remote_user:
        remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
            name=sender_user["name"]
        )
        try:
            _check_schools_and_classes(
                remote_user,
                new_prim_school,
                new_schools={new_prim_school, new_add_school},
                new_school_classes=new_value["school_classes"],
            )
        except AssertionError:
            time_taken = time.time() - start
            assert (
                time_taken < WAIT_FOR_REPLICATION_TIMEOUT
            ), f"took more than {WAIT_FOR_REPLICATION_TIMEOUT}s: {traceback.format_exc()}"


@pytest.mark.parametrize("role", ["student", "teacher"])
@pytest.mark.asyncio
async def test_add_additional_schools(
    make_school_authority,
    school_auth_config_kelvin,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
    role,
):
    """
    Tests if for a user receiving an additional school, the values are properly distributed by
    the ucsschool-id-connector (Bug 54411)
    """
    target_1 = school_auth_host_configs["traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    auth_school_mapping = await create_schools([(school_auth1, 2)])
    ou_auth1_1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    await save_mapping({ou_auth1_1: school_auth1.name, ou_auth1_2: school_auth1.name})
    sender_user: Dict[str, Any] = await make_sender_user(ous=[ou_auth1_1], roles=(role,))
    print(
        f"Created user {sender_user['name']} with school={sender_user['school']!r} and "
        f"and schools={sender_user['schools']!r} on sender."
    )
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_1),
        name=sender_user["name"],
    )
    old_school = ou_auth1_1
    new_school = ou_auth1_2
    new_value = {
        "school_classes": {new_school: [random_name()], old_school: [random_name()]},
        "school": old_school,
        "schools": [old_school, new_school],
    }

    print(f"Changing user on sender: {new_value!r}")
    await change_properties(kelvin_session(docker_hostname), sender_user["name"], new_value)
    sender_user_kelvin = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    print(
        f"User was modified at sender, has now school={sender_user_kelvin.school!r} "
        f"schools={sender_user_kelvin.schools!r} "
        f"school_classes={sender_user_kelvin.school_classes!r}."
    )
    _check_schools_and_classes(
        sender_user_kelvin,
        old_school,
        new_schools={old_school, new_school},
        new_school_classes=new_value["school_classes"],
    )

    start = time.time()
    remote_user = None
    while not remote_user:
        remote_user: User = await UserResource(session=kelvin_session(target_1)).get(
            name=sender_user["name"]
        )
        try:
            _check_schools_and_classes(
                remote_user,
                old_school,
                new_schools={old_school, new_school},
                new_school_classes=new_value["school_classes"],
            )
        except AssertionError:
            time_taken = time.time() - start
            assert (
                time_taken < WAIT_FOR_REPLICATION_TIMEOUT
            ), f"took more than {WAIT_FOR_REPLICATION_TIMEOUT}s: {traceback.format_exc()}"
