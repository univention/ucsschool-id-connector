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
from unittest.mock import MagicMock, patch

import pytest

from ucsschool_id_connector.models import School2SchoolAuthorityMapping

all_roles_mapping = {
    "users": 1,
    "users_student": 2,
    "users_teacher": 3,
    "users_staff": 4,
    "users_school_admin": 5,
}


@pytest.mark.parametrize(
    "mapping,expected",
    [
        ({"School1": "auth1", "School2": "auth2", "School3": "auth1"}, ["School1", "School3"]),
        ({}, []),
        ({"School1": "auth2"}, []),
    ],
)
@pytest.mark.asyncio
async def test_handled_schools(mapping, expected, idc_defaults, kelvin_school_authority_configuration):

    school_auth = kelvin_school_authority_configuration()
    school_auth.name = "auth1"
    school2school_auth_mapping = School2SchoolAuthorityMapping(mapping=mapping)
    with patch.object(
        idc_defaults.users_kelvin.KelvinPerSAUserDispatcher,
        "school_2_school_authority_mapping",
    ) as mapping_mock:
        dispatcher = idc_defaults.users_kelvin.KelvinPerSAUserDispatcher(school_auth, "kelvin")
        mapping_mock.return_value = school2school_auth_mapping
        handled_schools = await dispatcher.handled_schools()
        handled_schools.sort()
        assert handled_schools == expected


@pytest.mark.parametrize(
    "mapping,handled_schools,roles,expected",
    [
        # basic cases
        ({"users": 1, "users_student": 2}, ["School1"], [], 1),
        ({"users": 1}, ["School1"], ["student:school:School1"], 1),
        ({"users": 1, "users_student": 2}, ["School1"], ["some:weird:role"], 1),
        ({"users": 1, "users_student": 2}, ["School1"], ["invalid_role_str"], 1),
        ({"users": 1, "users_student": 2}, ["School1"], ["student:school:School1"], 2),
        # school distinction
        ({"users": 1, "users_student": 2}, ["School1"], ["student:school:School2"], 1),
        (
            {"users": 1, "users_student": 2, "users_teacher": 3},
            ["School1"],
            ["teacher:school:School2", "student:school:School1"],
            2,
        ),
        (
            {"users": 1, "users_student": 2, "users_teacher": 3},
            ["School1", "School2"],
            ["teacher:school:School2", "student:school:School1"],
            3,
        ),
        # order (users[1]<student[2]<teacher[3]<staff[4]<school_admin[5])
        (all_roles_mapping, ["School1"], ["student:school:School1", "school_admin:school:School1"], 5),
        (all_roles_mapping, ["School1"], ["student:school:School1", "staff:school:School1"], 4),
        (all_roles_mapping, ["School1"], ["student:school:School1", "teacher:school:School1"], 3),
        (all_roles_mapping, ["School1"], ["student:school:School1"], 2),
        (all_roles_mapping, ["School1"], [], 1),
        # fallbacks both teacher and staff, no staff mapping -> fallback to teacher
        (
            {"users": 1, "users_teacher": 3},
            ["School1"],
            ["staff:school:School1", "teacher:school:School1"],
            3,
        ),
        (
            {"users": 1, "users_student": 2},
            ["School1"],
            ["staff:school:School1", "teacher:school:School1"],
            1,
        ),
    ],
)
@pytest.mark.asyncio
async def test__get_role_specific_mapping(
    mapping, handled_schools, roles, expected, kelvin_school_authority_configuration, idc_defaults
):
    school_auth = kelvin_school_authority_configuration()
    school_auth.name = "auth1"
    dispatcher = idc_defaults.users_kelvin.KelvinPerSAUserDispatcher(school_auth, "kelvin")
    with patch.object(dispatcher, "handled_schools") as handled_schools_mock:
        handled_schools_mock.return_value = handled_schools
        actual_mapping = await dispatcher._get_role_specific_mapping(roles, mapping)
        assert actual_mapping == expected


@pytest.mark.asyncio
async def test_correct_mapping_used(idc_defaults, kelvin_school_authority_configuration):
    with patch(
        "ucsschool_id_connector_defaults.user_handler_base"
        ".PerSchoolAuthorityUserDispatcherBase.map_attributes"
    ) as map_attr_mock:
        dispatcher = idc_defaults.users_kelvin.KelvinPerSAUserDispatcher(
            kelvin_school_authority_configuration(), "kelvin"
        )
        with patch.object(dispatcher, "_get_role_specific_mapping") as get_role_mapping_mock:
            get_role_mapping_mock.return_value = 1
            obj = MagicMock()
            await dispatcher.map_attributes(obj, {})
            map_attr_mock.assert_called_once_with(obj, 1)
