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
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ucsschool_id_connector.models import School2SchoolAuthorityMapping, SchoolAuthorityConfiguration
from ucsschool_id_connector.plugins import plugin_manager


class LDAPAccessMock:
    def __init__(self):
        self._users = {}
        self._make_user("user1", ["student:school:School1"])
        self._make_user("user2", ["teacher:school:School1"])
        self._make_user("user3", ["student:school:School1"])
        self._make_user("user4", ["student:school:School2"])

    def _make_user(self, username, roles):
        new_user = MagicMock()
        new_user.attributes = {"ucsschoolRole": roles}
        new_user.username = username
        self._users[username] = new_user

    async def get_user(self, username, *args, **kwargs):
        return self._users.get(username, None)


@pytest.fixture()
def school_auth_config(kelvin_school_authority_configuration):
    def _school_auth_config(ignore_roles: List[str]):
        config: SchoolAuthorityConfiguration = kelvin_school_authority_configuration()
        config.name = "auth1"
        config.plugin_configs["kelvin-partial-group-sync"] = config.plugin_configs["kelvin"]
        del config.plugin_configs["kelvin"]
        config.plugin_configs["kelvin-partial-group-sync"]["school_classes_ignore_roles"] = ignore_roles
        return config

    return _school_auth_config


@pytest.fixture()
def school_class_handler(idc_defaults, school_auth_config):
    def _school_class_handler(ignore_roles):
        config = school_auth_config(ignore_roles)
        plugin = plugin_manager.get_plugin("kelvin-partial-group-sync")
        school_class_handler = plugin.school_class_handler.handler(config, "kelvin-partial-group-sync")
        school_class_handler.school_authority = config
        return school_class_handler

    return _school_class_handler


@pytest.mark.parametrize(
    "ignore_roles,roles,expected",
    [
        ([], ["student:school:School1"], False),
        (["student"], ["student:school:School1"], True),
        ([], ["some:weird:role"], False),
        ([], ["invalid_role_str"], False),
        (["student", "teacher"], ["teacher:school:School1"], True),
        (["student"], ["student:school:School2"], False),
    ],
)
@pytest.mark.asyncio
async def test__check_user_ignore(ignore_roles, roles, expected, school_class_handler):
    sc_handler = school_class_handler(ignore_roles)
    with patch.object(sc_handler, "school_2_school_authority_mapping") as mapping_mock:
        mapping_mock.return_value = School2SchoolAuthorityMapping(
            mapping={"School1": "auth1", "School2": "auth2", "School3": "auth1"}
        )
        assert await sc_handler._check_user_ignore(roles) == expected


@pytest.mark.parametrize(
    "local_users,remote_users,handled_schools,expected,ignore_roles",
    [
        # Normal behavior
        (
            ["user1", "user2", "user3"],
            ["user1", "user2", "user3"],
            ["School1"],
            ["user1", "user2", "user3"],
            [],
        ),
        (["user1", "user2", "user3"], ["user1", "user2"], ["School1"], ["user1", "user2", "user3"], []),
        (["user1", "user2"], ["user1", "user2", "user3"], ["School1"], ["user1", "user2"], []),
        # New behavior
        (
            ["user1", "user2"],
            ["user1", "user2", "unkown"],
            ["School1"],
            ["unkown", "user1", "user2"],
            [],
        ),
        (["user1", "user2", "user3"], ["user2", "user3"], ["School1"], ["user2", "user3"], ["student"]),
        ([], ["user2", "user3"], ["School1"], ["user3"], ["student"]),
        # Users from other schools are removed, regardless of their role
        (["user2"], ["user4"], ["School1"], ["user2"], []),
        ([], ["user4"], ["School1"], [], ["student"]),
    ],
)
@pytest.mark.asyncio
@patch(
    "ucsschool_id_connector_defaults.school_classes_kelvin."
    "KelvinPerSASchoolClassDispatcher._handle_attr_users"
)
async def test__handle_attr_users(
    handle_mock, local_users, remote_users, handled_schools, expected, ignore_roles, school_class_handler
):
    sc_handler = school_class_handler(ignore_roles)
    handle_mock.return_value = local_users
    sc_handler._get_remote_usernames = AsyncMock(return_value=remote_users)
    sc_handler._ldap_access = LDAPAccessMock()
    obj = MagicMock()
    obj.object = {"name": "School1-1a"}
    sc_handler.handled_schools = AsyncMock(return_value=handled_schools)
    actual_users = await sc_handler._handle_attr_users(obj)
    actual_users.sort()
    assert actual_users == expected
