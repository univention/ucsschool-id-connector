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

import copy
import time
from typing import Any, Dict, Iterable
from urllib.parse import urlsplit

import faker
import pytest

from ucsschool.kelvin.client import NoObject, User, UserResource

try:
    from simplejson.errors import JSONDecodeError
except ImportError:  # pragma: no cover
    JSONDecodeError = ValueError

fake = faker.Faker()


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
    for school_url in user["schools"]:
        school = school_url.rstrip("/").split("/")[-1]
        if mapping[school] != auth:
            result_user["schools"].remove(school_url)
    for class_ou in user["school_classes"].keys():
        if mapping[class_ou] != auth:
            del result_user["school_classes"][class_ou]
    return result_user


@pytest.mark.asyncio
async def test_create_user(
    make_school_authority,
    make_sender_user,
    school_auth_config,
    save_mapping,
    create_schools,
    docker_hostname,
    check_password,
    compare_user,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
):
    """
    Tests if ucsschool_id_connector distributes a newly created User to the correct school
    authorities.
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    target_ip_2 = school_auth_host_configs["IP_traeger2"]
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = auth_school_mapping[school_auth2.name][0]
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
        sender_user: Dict[str, Any] = make_sender_user(ous=ous)
        # verify user on sender system
        await UserResource(session=kelvin_session(docker_hostname)).get(name=sender_user["name"])
        check_password(sender_user["name"], sender_user["password"], docker_hostname)
        print(f"Created user {sender_user['name']!r} on sender, looking for it in auth1...")
        user_remote: User = await wait_for_kelvin_object_exists(
            resource_cls=UserResource,
            method="get",
            session=kelvin_session(target_ip_1),
            name=sender_user["name"],
        )
        print(f"Found {user_remote!r}, checking its attributes...")
        expected_target_user1 = filter_ous(sender_user, school_auth1.name, mapping)
        compare_user(expected_target_user1, user_remote.as_dict())
        check_password(
            sender_user["name"],
            sender_user["password"],
            urlsplit(school_auth1.url).netloc,
        )
        if ou_auth2 in ous:
            print(f"User should also be in OU2 ({ou_auth2!r}), checking...")
            user_remote: User = await wait_for_kelvin_object_exists(
                resource_cls=UserResource,
                method="get",
                session=kelvin_session(target_ip_2),
                name=sender_user["name"],
            )
            expected_target_user2 = filter_ous(sender_user, school_auth2.name, mapping)
            compare_user(expected_target_user2, user_remote.as_dict())
            check_password(
                sender_user["name"],
                sender_user["password"],
                urlsplit(school_auth2.url).netloc,
            )
        else:
            print(f"User should NOT be in OU2 ({ou_auth2!r}), checking...")
            with pytest.raises(NoObject):
                await UserResource(session=kelvin_session(target_ip_2)).get(name=sender_user["name"])


@pytest.mark.asyncio
async def test_delete_user(
    make_school_authority,
    make_sender_user,
    school_auth_config,
    save_mapping,
    create_schools,
    kelvin_auth_header,
    url_fragment,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
    wait_for_kelvin_object_not_exists,
    http_request,
):
    """
    Tests if ucsschool_id_connector distributes the deletion of an existing
    user correctly.
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    target_ip_2 = school_auth_host_configs["IP_traeger2"]
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
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
    sender_user = make_sender_user(ous=(ou_auth1, ou_auth2))
    print(f"Created user {sender_user['name']!r} in sender. Looking for it now in auth1...")
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_ip_1),
        name=sender_user["name"],
    )
    print(f"Found user {sender_user['name']!r} in ou_auth1. Looking for it now in auth2...")
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_ip_2),
        name=sender_user["name"],
    )
    print(f"Deleting user {sender_user['name']!r} in sender...")
    http_request(
        "delete",
        f"{url_fragment}/users/{sender_user['name']}",
        verify=True,
        headers=kelvin_auth_header,
        expected_statuses=(204,),
    )
    print(
        f"User {sender_user['name']!r} was deleted in sender, waiting for it to "
        f"disappear in ou_auth1..."
    )
    await wait_for_kelvin_object_not_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_ip_1),
        name=sender_user["name"],
    )
    print(
        f"User {sender_user['name']!r} disappeared in ou_auth1, waiting for it to "
        f"also disappear in ou_auth2..."
    )
    await wait_for_kelvin_object_not_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_ip_2),
        name=sender_user["name"],
    )


@pytest.mark.asyncio
async def test_modify_user(
    make_school_authority,
    make_sender_user,
    school_auth_config,
    save_mapping,
    create_schools,
    docker_hostname,
    check_password,
    compare_user,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
    url_fragment,
    kelvin_auth_header,
    http_request,
):
    """
    Tests if the modification of a user is properly distributed to the school
    authority
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config(1))
    school_auth2 = await make_school_authority(**school_auth_config(2))
    auth_school_mapping = create_schools([(school_auth1, 2), (school_auth2, 1)])
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
    sender_user = make_sender_user(ous=[ou_auth1])
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
        session=kelvin_session(target_ip_1),
        name=sender_user["name"],
    )
    check_password(sender_user["name"], sender_user["password"], urlsplit(school_auth1.url).netloc)
    # Modify user
    new_value = {
        "firstname": fake.first_name(),
        "lastname": fake.last_name(),
        "disabled": not sender_user["disabled"],
        "birthday": fake.date_of_birth(minimum_age=6, maximum_age=67).strftime("%Y-%m-%d"),
    }
    response = http_request(
        "patch",
        f"{url_fragment}/users/{sender_user['name']}",
        verify=False,
        headers=kelvin_auth_header,
        json_data=new_value,
    )
    user_on_host: Dict[str, Any] = response.json()
    compare_user(new_value, user_on_host, new_value.keys())
    user_on_host: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    compare_user(new_value, user_on_host.as_dict(), new_value.keys())
    # Check if user was modified on target host
    timeout = 40
    while timeout > 0:
        time.sleep(5)
        timeout -= 5
        remote_user: User = await UserResource(session=kelvin_session(target_ip_1)).get(
            name=sender_user["name"]
        )
        if remote_user.firstname == new_value["firstname"]:
            break
    else:
        print(f"Waited {timeout}s without the user changing its firstname, continuing...")

    remote_user: User = await UserResource(session=kelvin_session(target_ip_1)).get(
        name=sender_user["name"]
    )
    compare_user(user_on_host.as_dict(), remote_user.as_dict())


@pytest.mark.asyncio
async def test_class_change(
    make_school_authority,
    school_auth_config,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    school_auth_host_configs,
    kelvin_session,
    wait_for_kelvin_object_exists,
    url_fragment,
    kelvin_auth_header,
    http_request,
):
    """
    Tests if the modification of a users class is properly distributed by
    ucsschool-id-connector.
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config(1))
    auth_school_mapping = create_schools([(school_auth1, 1)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    await save_mapping({ou_auth1: school_auth1.name})
    sender_user = make_sender_user(ous=[ou_auth1])
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
        session=kelvin_session(target_ip_1),
        name=sender_user["name"],
    )
    assert user_auth1.school_classes == sender_user["school_classes"]
    print(f"2. User was created in auth1 with school_classes={user_auth1.school_classes!r}.")
    new_value = {"school_classes": {ou_auth1: [random_name()]}}
    print(f"3. setting new value for school_classes on sender: {new_value!r}")
    response = http_request(
        "patch",
        f"{url_fragment}/users/{sender_user['name']}",
        verify=False,
        headers=kelvin_auth_header,
        json_data=new_value,
    )
    school_classes_at_sender = response.json()["school_classes"]
    assert school_classes_at_sender == new_value["school_classes"]
    sender_user_kelvin: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    assert sender_user_kelvin.school_classes == new_value["school_classes"]
    print(f"4. User was modified at sender, has now school_classes={school_classes_at_sender!r}.")
    # Check if user was modified on target host
    timeout = 40
    while timeout > 0:
        time.sleep(5)
        timeout -= 5
        remote_user: User = await UserResource(session=kelvin_session(docker_hostname)).get(
            name=sender_user["name"]
        )
        if remote_user.school_classes == new_value["school_classes"]:
            break
    else:
        print(f"Waited {timeout}s without the users school classes changing, continuing...")

    assert remote_user.school_classes == new_value["school_classes"]


@pytest.mark.asyncio
async def test_school_change(
    make_school_authority,
    school_auth_config,
    create_schools,
    save_mapping,
    make_sender_user,
    docker_hostname,
    random_name,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
    url_fragment,
    kelvin_auth_header,
    http_request,
):
    """
    Tests if the modification of a users school is properly distributed by
    ucsschool-id-connector.
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    school_auth1 = await make_school_authority(**school_auth_config(1))
    auth_school_mapping = create_schools([(school_auth1, 2)])
    ou_auth1 = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = auth_school_mapping[school_auth1.name][1]
    await save_mapping({ou_auth1: school_auth1.name, ou_auth1_2: school_auth1.name})
    sender_user = make_sender_user(ous=[ou_auth1])
    print(
        f"Created user {sender_user['name']} with school={sender_user['school']!r} and "
        f"and schools={sender_user['schools']!r} on sender."
    )
    await wait_for_kelvin_object_exists(
        resource_cls=UserResource,
        method="get",
        session=kelvin_session(target_ip_1),
        name=sender_user["name"],
    )
    new_school = ou_auth1_2
    new_value = {
        "school_classes": {new_school: [random_name()]},
        "school": f"{url_fragment}/schools/{new_school}",
        "schools": [f"{url_fragment}/schools/{new_school}"],
    }

    print(f"Changing user on sender: {new_value!r}")
    http_request(
        "patch",
        f"{url_fragment}/users/{sender_user['name']}",
        verify=False,
        headers=kelvin_auth_header,
        json_data=new_value,
    )
    sender_user_kelvin: User = await UserResource(session=kelvin_session(docker_hostname)).get(
        name=sender_user["name"]
    )
    print(
        f"User was modified at sender, has now school={sender_user_kelvin.school!r} "
        f"schools={sender_user_kelvin.schools!r} "
        f"school_classes={sender_user_kelvin.school_classes!r}."
    )
    assert sender_user_kelvin.school == new_school
    assert sender_user_kelvin.schools == [new_school]
    assert sender_user_kelvin.school_classes == new_value["school_classes"]

    timeout = 40
    while timeout > 0:
        time.sleep(5)
        timeout -= 5
        remote_user: User = await UserResource(session=kelvin_session(target_ip_1)).get(
            name=sender_user["name"]
        )
        try:
            assert remote_user.school == new_school
            assert remote_user.schools == [new_school]
            assert remote_user.school_classes == new_value["school_classes"]
            break
        except AssertionError:
            pass
    else:
        print(f"Waited {timeout}s without the user changing its school, continuing...")
    assert remote_user.school == new_school
    assert remote_user.schools == [new_school]
    assert remote_user.school_classes == new_value["school_classes"]
