# -*- coding: utf-8 -*-

# Copyright 2023 Univention GmbH
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

import faker
import pytest

from ucsschool.kelvin.client import SchoolClass, SchoolClassResource

fake = faker.Faker()


def compare_school_classes(sc1: SchoolClass, sc2: SchoolClass):
    assert sc1.name.lower() == sc2.name.lower()
    assert sc1.school.lower() == sc2.school.lower()
    assert sc1.description == sc2.description
    assert {u.lower() for u in sc1.users} == {u.lower() for u in sc2.users}


@pytest.mark.asyncio
@pytest.mark.parametrize("ou_case_correct", (True, False))
async def test_create_school_class(
    make_school_authority,
    school_auth_config_kelvin,
    save_mapping,
    create_schools,
    kelvin_session,
    school_auth_host_configs,
    wait_for_kelvin_object_exists,
    make_kelvin_school_class_on_id_connector,
    scramble_case,
    ou_case_correct: bool,
):
    """
    Tests if ucsschool_id_connector distributes a newly created SchoolClass to the correct school
    authorities.
    """
    target_ip_1 = school_auth_host_configs["IP_traeger1"]
    target_ip_2 = school_auth_host_configs["IP_traeger2"]
    school_auth1 = await make_school_authority(**school_auth_config_kelvin(1))
    school_auth2 = await make_school_authority(**school_auth_config_kelvin(2))
    auth_school_mapping = await create_schools([(school_auth1, 2), (school_auth2, 1)])
    ou_auth1 = ou_auth1_correct = auth_school_mapping[school_auth1.name][0]
    ou_auth1_2 = ou_auth1_2_correct = auth_school_mapping[school_auth1.name][1]
    ou_auth2 = ou_auth2_correct = auth_school_mapping[school_auth2.name][0]
    if not ou_case_correct:
        ou_auth1 = scramble_case(ou_auth1_correct)
        assert ou_auth1 != ou_auth1_correct
        ou_auth1_2 = scramble_case(ou_auth1_2_correct)
        assert ou_auth1_2 != ou_auth1_2_correct
        ou_auth2 = scramble_case(ou_auth2_correct)
        assert ou_auth2 != ou_auth2_correct
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

    print(f"===> Creating school class on sender in OU1 on auth1 (ou_auth1={ou_auth1!r})...")
    class_name_1 = f"test.sc.{fake.first_name()[:8]}.{fake.last_name()[:8]}"
    sc1: SchoolClass = await make_kelvin_school_class_on_id_connector(
        ou_auth1, class_name_1, class_name_1, []
    )
    assert class_name_1 == sc1.name
    print(f"Created school class {sc1.name!r} on sender, looking for it in auth1...")
    sc1_remote: SchoolClass = await wait_for_kelvin_object_exists(
        resource_cls=SchoolClassResource,
        method="get",
        session=kelvin_session(target_ip_1),
        name=sc1.name,
        school=sc1.school,
    )
    print(f"Found {sc1_remote!r}, checking its attributes...")
    compare_school_classes(sc1, sc1_remote)

    print(f"===> Creating school class on sender in OU2 on auth1 (ou_auth1_2={ou_auth1_2!r})...")
    class_name_1_2 = f"test.sc.{fake.first_name()[:8]}.{fake.last_name()[:8]}"
    sc1_2 = await make_kelvin_school_class_on_id_connector(ou_auth1_2, class_name_1_2, class_name_1, [])
    assert class_name_1_2 == sc1_2.name
    print(f"Created school class {sc1_2.name!r} on sender, looking for it in auth1...")
    sc1_2_remote: SchoolClass = await wait_for_kelvin_object_exists(
        resource_cls=SchoolClassResource,
        method="get",
        session=kelvin_session(target_ip_1),
        name=sc1_2.name,
        school=sc1_2.school,
    )
    print(f"Found {sc1_2_remote!r}, checking its attributes...")
    compare_school_classes(sc1_2, sc1_2_remote)

    print(f"===> Creating school class on sender in OU on auth2 (ou_auth2={ou_auth2!r})...")
    class_name_2 = f"test.sc.{fake.first_name()[:8]}.{fake.last_name()[:8]}"
    sc2 = await make_kelvin_school_class_on_id_connector(ou_auth2, class_name_2, class_name_1, [])
    assert class_name_2 == sc2.name
    print(f"Created school class {sc2.name!r} on sender, looking for it in auth1...")
    sc2_remote: SchoolClass = await wait_for_kelvin_object_exists(
        resource_cls=SchoolClassResource,
        method="get",
        session=kelvin_session(target_ip_2),
        name=sc2.name,
        school=sc2.school,
    )
    print(f"Found {sc2_remote!r}, checking its attributes...")
    compare_school_classes(sc2, sc2_remote)
