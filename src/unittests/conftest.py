# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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
import random
import string
from functools import partial
from typing import Any, Dict, List
from unittest.mock import MagicMock

import factory
import pytest
import ujson
from faker import Faker

import id_sync.models

fake = Faker()


class UserPasswordsFactory(factory.Factory):
    class Meta:
        model = id_sync.models.UserPasswords

    userPassword = factory.List(
        [
            "{crypt}$6$PHNzGeWYEDELE2km$0.MZqUmEEvDzCKGCyrb9Wrq3n3g3flTm8nFRwtx1/O"
            "0iXY7KhM48WssN0.y2WmBHSQ2CRmm2de9fGYevqQDxA1"
        ]
    )
    sambaNTPassword = "470A9B46CC8EC53B76D7AEB21B9A9255"
    krb5Key = factory.LazyFunction(
        lambda: [fake.password().encode(), fake.password().encode()]
    )
    krb5KeyVersionNumber = factory.Faker("pyint", min_value=1)
    sambaPwdLastSet = factory.Faker("pyint", min_value=1566029000, max_value=1566029100)


class ListenerObjectFactory(factory.Factory):
    class Meta:
        model = id_sync.models.ListenerObject

    dn = factory.LazyFunction(
        lambda: f"uid={fake.first_name()},cn=users,"
        f"dc={fake.first_name()},"
        f"dc={fake.first_name()}"
    )
    id = factory.Faker("uuid4")
    udm_object_type = factory.LazyFunction(
        lambda: f"{fake.first_name()}/" f"{fake.first_name()}"
    )
    action = factory.LazyFunction(lambda: id_sync.models.ListenerActionEnum.add_mod)


class ListenerAddModifyObjectFactory(ListenerObjectFactory):
    class Meta:
        model = id_sync.models.ListenerAddModifyObject

    object = factory.Dict({})
    options = factory.List([])


class ListenerUserAddModifyObjectFactory(ListenerAddModifyObjectFactory):
    class Meta:
        model = id_sync.models.ListenerUserAddModifyObject

    object = factory.LazyFunction(lambda: _listener_dump_user_object()["object"])
    options = factory.List(["default"])
    udm_object_type = "users/user"
    user_passwords = factory.SubFactory(UserPasswordsFactory)


class ListenerRemoveObjectFactory(ListenerObjectFactory):
    action = id_sync.models.ListenerActionEnum.delete


class SchoolAuthorityConfigurationFactory(factory.Factory):
    class Meta:
        model = id_sync.models.SchoolAuthorityConfiguration

    name = factory.Faker("first_name")
    active = factory.LazyFunction(lambda: True)
    url = factory.Faker("uri")
    password = factory.Faker("password")
    mapping = factory.Dict(
        {
            "firstname": "firstname",
            "lastname": "lastname",
            "username": "name",
            "disabled": "disabled",
            "school": "school",
            "schools": "schools",
            "school_classes": "school_classes",
            "source_uid": "source_uid",
            "roles": "roles",
            "record_uid": "record_uid",
        }
    )
    passwords_target_attribute = "id_sync_pw"


class School2SchoolAuthorityMappingFactory(factory.Factory):
    class Meta:
        model = id_sync.models.School2SchoolAuthorityMapping

    mapping = factory.LazyFunction(lambda: dict(
        (fake.domain_word(), fake.domain_word())
        for _ in range(fake.pyint(2, 10))
    ))


def _listener_dump_user_object(
    base_dn: str = None,
    ou: str = None,
    ous: List[str] = None,
    options: List[str] = None,
    source_uid: str = None,
) -> Dict[str, Any]:
    base_dn = (
        base_dn
        or f"dc={fake.domain_name().split('.')[0]},"
        f"dc={fake.domain_name().split('.')[-1]}"
    )
    ou = ou or fake.domain_word()
    ous = ous or [ou]
    options = options or []
    if "default" not in options:
        options.append("default")
    if not {"ucsschoolStaff", "ucsschoolStudent", "ucsschoolTeacher"}.intersection(
        set(options)
    ):
        options.append("ucsschoolTeacher")
    source_uid = source_uid or "TESTID"
    fn = fake.first_name()
    ln = fake.last_name()
    un = fake.user_name()
    return {
        "dn": f"uid={un},cn=users,ou={ou},{base_dn}",
        "id": fake.uuid4(),
        "object": {
            "disabled": "0",
            "displayName": f"{fn} {ln}",
            "e-mail": [f"{un}1@example.com", f"{un}2@example.com"],
            "firstname": fn,
            "gecos": f"{fn} {ln}",
            "gidNumber": str(fake.pyint(4000, 60000)),
            "groups": [f"cn=Domain Users,cn=groups,{base_dn}"],
            "lastname": ln,
            "locked": "0",
            "lockedTime": "0",
            "mailForwardCopyToSelf": "0",
            "mailUserQuota": "0",
            "password": "{crypt}$6$PHNzGeWYEDELE2km$0.MZqUmEEvDzCKGCyrb9Wrq3n3g3"
            "flTm8nFRwtx1/O0iXY7KhM48WssN0.y2WmBHSQ2CRmm2de9fGYevqQDxA1",
            "passwordexpiry": None,
            "phone": [fake.phone_number()],
            "primaryGroup": f"cn=Domain Users,cn=groups,{base_dn}",
            "record_uid": fake.user_name(),
            "sambaRID": str(fake.pyint(4000, 60000)),
            "school": ous,
            "shell": "/bin/bash",
            "source_uid": source_uid,
            "uidNumber": str(fake.pyint(4000, 60000)),
            "unixhome": f"/home/{fn}",
            "unlockTime": "",
            "userexpiry": None,
            "username": un,
        },
        "options": options,
        "udm_object_type": "users/user",
    }


@pytest.fixture
def listener_dump_user_object():
    def _func(
        base_dn: str = None,
        ou: str = None,
        ous: List[str] = None,
        options: List[str] = None,
        source_uid: str = None,
    ) -> Dict[str, Any]:
        return _listener_dump_user_object(
            base_dn=base_dn, ou=ou, ous=ous, options=options, source_uid=source_uid
        )

    return _func


# enable this, when you need it
#
# @pytest.fixture
# def user_passwords_object():
#     return lambda: UserPasswordsFactory()


@pytest.fixture
def listener_user_add_modify_object(listener_dump_user_object):
    def _func(
        base_dn: str = None,
        ou: str = None,
        ous: List[str] = None,
        options: List[str] = None,
        source_uid: str = None,
    ) -> id_sync.models.ListenerUserAddModifyObject:
        listener_dump_obj = listener_dump_user_object(
            base_dn=base_dn, ou=ou, ous=ous, options=options, source_uid=source_uid
        )
        obj = ListenerUserAddModifyObjectFactory(
            dn=listener_dump_obj["dn"],
            object=listener_dump_obj["object"],
            options=listener_dump_obj["options"],
        )
        return obj

    return _func


# enable this, when you need it
#
# @pytest.fixture
# def listener_user_remove_object():
#     def _func() -> id_sync.models.ListenerRemoveObject:
#         obj = ListenerRemoveObjectFactory()
#         obj.udm_object_type = "users/user"
#         return obj
#
#     return _func


@pytest.fixture
def school_authority_configuration():
    return lambda: SchoolAuthorityConfigurationFactory()


@pytest.fixture
def random_name():
    def _func(ints=True) -> str:
        name = list(string.ascii_letters)
        if ints:
            name.extend(list(string.digits))
        random.shuffle(name)
        return "".join(name[: random.randint(8, 12)])

    return _func


@pytest.fixture
def random_int():
    def _func(start=0, end=12) -> int:
        return fake.pyint(start, end)

    return _func


@asyncio.coroutine
def recv_string(obj):
    yield from asyncio.sleep(0.1)
    return ujson.dumps(obj)


@pytest.fixture
def zmq_socket():
    def _func(recv_string_args):
        socket = MagicMock()
        socket.send_string.return_value = {}
        socket.recv_string = partial(recv_string, recv_string_args)
        return socket

    return _func


@pytest.fixture
def school2school_authority_mapping():
    return lambda: School2SchoolAuthorityMappingFactory()
