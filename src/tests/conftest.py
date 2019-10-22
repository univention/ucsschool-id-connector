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
import shutil
import string
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import factory
import pytest
import ujson
from faker import Faker

import id_sync.constants
import id_sync.models
import id_sync.plugin_loader
import id_sync.plugins
import id_sync.utils

fake = Faker()


DEFAULT_DUMMY_PLUGIN = """
from id_sync.utils import ConsoleAndFileLogging
from id_sync.plugins import hook_impl, plugin_manager
logger = ConsoleAndFileLogging.get_logger(__name__)
class DefaultDummyPlugin:
    @hook_impl
    def dummy_func(self, arg1, arg2):
        logger.info("Running DefaultDummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
        return arg1 - arg2
plugin_manager.register(DefaultDummyPlugin())
"""

CUSTOM_DUMMY_PLUGIN = """
from id_sync.utils import ConsoleAndFileLogging
from id_sync.plugins import hook_impl, plugin_manager
from {package_name}.{module_name} import ExampleTestClass
logger = ConsoleAndFileLogging.get_logger(__name__)
class DummyPlugin:
    @hook_impl
    def dummy_func(self, arg1, arg2):
        logger.info("Running DummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
        example_obj = ExampleTestClass()
        res = example_obj.add(arg1, arg2)
        assert res == arg1 + arg2
        return res
plugin_manager.register(DummyPlugin())
"""

CUSTOM_TEST_MODULE_IN_PACKAGE = """
from id_sync.utils import ConsoleAndFileLogging
logger = ConsoleAndFileLogging.get_logger(__name__)
class ExampleTestClass:
    def add(self, arg1, arg2):
        logger.info("Running ExampleTestClass.example_func() with arg1=%r arg2=%r.", arg1, arg2)
        return arg1 + arg2
"""

# Monkey patch get_logger() here, so it won't have to be included as a
# fixture everywhere.
_ori_get_logger = id_sync.utils.ConsoleAndFileLogging.get_logger


def utils_get_logger(
    name: str = None, path: Path = id_sync.constants.LOG_FILE_PATH_QUEUES
):
    log_dir = Path(mkdtemp())
    if path:
        path = log_dir / path.name
    print(f"\n **** log directory is: {path} ****")
    return _ori_get_logger(name, path)


id_sync.utils.ConsoleAndFileLogging.get_logger = utils_get_logger


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

    mapping = factory.LazyFunction(
        lambda: dict(
            (fake.domain_word(), fake.domain_word()) for _ in range(fake.pyint(2, 10))
        )
    )


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


@pytest.fixture
def user_passwords_object():
    return lambda: UserPasswordsFactory()


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


class DummyPluginSpec:
    @id_sync.plugins.hook_spec(firstresult=True)
    def dummy_func(self, arg1, arg2):
        """An example hook."""


@pytest.fixture(scope="session")
def mock_plugin_impls():
    # replace /var/lib/univention-appcenter/apps/id-sync with path below /tmp
    # and /id-sync/src with ../..
    tmp_dir = Path(mkdtemp(dir="/tmp"))
    default_package_dir = Path(__file__).parent.parent / "plugins/packages"
    custom_package_base_dir = tmp_dir / "plugins/packages"
    custom_package_base_dir.mkdir(parents=True)
    mock_package_dirs = (default_package_dir, custom_package_base_dir)
    default_plugin_dir = Path(__file__).parent.parent / "plugins/plugins"
    custom_plugin_dir = tmp_dir / "plugins/plugins"
    custom_plugin_dir.mkdir(parents=True)
    mock_plugin_dirs = (default_plugin_dir, custom_plugin_dir)

    custom_package_name = fake.pystr(min_chars=5, max_chars=8)
    custom_package_dir = custom_package_base_dir / custom_package_name
    custom_package_dir.mkdir(parents=True)
    custom_module_name = fake.pystr(min_chars=5, max_chars=8)
    custom_module_path = custom_package_dir / f"{custom_module_name}.py"
    with open(custom_module_path, "w") as fp:
        fp.write(CUSTOM_TEST_MODULE_IN_PACKAGE)
    custom_plugin_name = fake.pystr(min_chars=5, max_chars=8)
    custom_plugin_path = custom_plugin_dir / f"{custom_plugin_name}.py"
    with open(custom_plugin_path, "w") as fp:
        fp.write(
            CUSTOM_DUMMY_PLUGIN.format(
                module_name=custom_module_name, package_name=custom_package_name
            )
        )
    default_plugin_name = fake.pystr(min_chars=5, max_chars=8)
    default_plugin_path = default_plugin_dir / f"{default_plugin_name}.py"
    with open(default_plugin_path, "w") as fp:
        fp.write(DEFAULT_DUMMY_PLUGIN)

    yield mock_plugin_dirs, mock_package_dirs

    id_sync.plugins.plugin_manager.unregister("DummyPlugin")
    id_sync.plugins.plugin_manager.unregister("DefaultDummyPlugin")
    shutil.rmtree(tmp_dir)
    default_plugin_path.unlink()
    for path in (default_plugin_dir / "__pycache__").glob(
        f"{default_plugin_name}.*.pyc"
    ):
        path.unlink()
    try:
        (default_plugin_dir / "__pycache__").rmdir()
    except OSError:
        pass


@pytest.fixture(scope="session")
def mock_plugin_spec():
    id_sync.plugins.plugin_manager.add_hookspecs(DummyPluginSpec)


@pytest.fixture(scope="session")
def db_path():
    path = mkdtemp(dir="/tmp")
    yield Path(path)
    shutil.rmtree(path)


@pytest.fixture
def mock_plugins(
    monkeypatch, mock_plugin_impls, mock_plugin_spec, user_passwords_object, db_path
):
    mock_plugin_dirs, mock_package_dirs = mock_plugin_impls
    fake_user_passwords_object = user_passwords_object()

    class LDAPAccess(MagicMock):
        async def get_passwords(self, username):
            return fake_user_passwords_object

    monkeypatch.setenv("ldap_base", "dc=foo,dc=bar")
    monkeypatch.setenv("ldap_server_name", "localhost")
    monkeypatch.setenv("ldap_server_port", "7389")

    with patch.object(
        id_sync.plugin_loader, "PLUGIN_PACKAGE_DIRS", mock_package_dirs
    ), patch.object(
        id_sync.plugin_loader, "PLUGIN_DIRS", mock_plugin_dirs
    ), patch.object(
        id_sync.constants, "OLD_DATA_DB_PATH", db_path
    ), patch(
        "id_sync.ldap_access.LDAPAccess", LDAPAccess
    ):

        id_sync.plugin_loader.load_plugins()

    yield mock_plugin_impls, db_path, fake_user_passwords_object


@pytest.fixture(scope="session")
def example_user_json_path_real():
    return Path(__file__).parent.parent / "example_user.json"


@pytest.fixture(scope="session")
def example_user_remove_json_path_real():
    return Path(__file__).parent.parent / "example_user_remove.json"


@pytest.fixture
def example_user_json_path_copy(example_user_json_path_real):
    def _func(temp_dir):
        with NamedTemporaryFile(
            delete=False, dir=str(temp_dir), suffix=".json"
        ) as fpw, open(example_user_json_path_real, "rb") as fpr:
            fpw.write(fpr.read())
            fpw.flush()
        return Path(fpw.name)

    return _func


@pytest.fixture
def example_user_remove_json_path_copy(example_user_remove_json_path_real):
    def _func(temp_dir):
        with NamedTemporaryFile(
            delete=False, dir=str(temp_dir), suffix=".json"
        ) as fpw, open(example_user_remove_json_path_real, "rb") as fpr:
            fpw.write(fpr.read())
            fpw.flush()
        return Path(fpw.name)

    return _func