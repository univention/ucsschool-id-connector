# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from ucsschool_id_connector.models import (
    ListenerActionEnum,
    ListenerUserAddModifyObject,
    SchoolAuthorityConfiguration,
    UnknownSchoolUserRole,
)

# Copyright 2020 Univention GmbH
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


def test_school_authority_configuration_password_is_secret_str(
    faker_obj, school_authority_configuration
):
    sac: SchoolAuthorityConfiguration = school_authority_configuration()
    password = faker_obj.password()
    sac_kwargs = sac.dict()
    sac_kwargs["plugin_configs"]["kelvin"]["password"] = password
    sac_new = SchoolAuthorityConfiguration(**sac_kwargs)
    assert isinstance(sac_new.plugin_configs["kelvin"]["password"], SecretStr)
    assert sac_new.plugin_configs["kelvin"]["password"].get_secret_value() == password


def test_school_authority_configuration_as_dict_pw_is_secrets(
    school_authority_configuration,
):
    sac: SchoolAuthorityConfiguration = school_authority_configuration()
    assert isinstance(sac.plugin_configs["kelvin"]["password"], SecretStr)
    password = sac.plugin_configs["kelvin"]["password"].get_secret_value()
    sac_as_dict_with_pw_as_secret = sac.dict()
    assert isinstance(sac_as_dict_with_pw_as_secret["plugin_configs"]["kelvin"]["password"], SecretStr)
    assert (
        sac_as_dict_with_pw_as_secret["plugin_configs"]["kelvin"]["password"].get_secret_value()
        == password
    )


@pytest.mark.parametrize("legal_guardians_set", (True, False))
@pytest.mark.parametrize("legal_wards_set", (True, False))
def test_legal_guardian_config_validation(
    school_authority_configuration,
    legal_guardians_set,
    legal_wards_set,
):
    sac: SchoolAuthorityConfiguration = school_authority_configuration()
    if legal_guardians_set:
        sac.plugin_configs["kelvin"]["mapping"]["users"]["ucsschoolLegalGuardian"] = "legal_guardians"
    if legal_wards_set:
        sac.plugin_configs["kelvin"]["mapping"]["users"]["ucsschoolLegalWard"] = "legal_wards"

    # Verify that if only one direction is configured, the expected error is thrown
    if legal_guardians_set != legal_wards_set:
        expected_error = pytest.raises(ValueError)
    else:
        expected_error = MagicMock()
    with expected_error:
        SchoolAuthorityConfiguration(**sac.dict())


def test_school_authority_configuration_as_dict_pw_is_str(
    school_authority_configuration,
):
    sac: SchoolAuthorityConfiguration = school_authority_configuration()
    assert isinstance(sac.plugin_configs["kelvin"]["password"], SecretStr)
    password = sac.plugin_configs["kelvin"]["password"].get_secret_value()
    sac_as_dict_with_pw_as_str = sac.dict_secrets_as_str()
    assert isinstance(sac_as_dict_with_pw_as_str["plugin_configs"]["kelvin"]["password"], str)
    assert sac_as_dict_with_pw_as_str["plugin_configs"]["kelvin"]["password"] == password


def test_listener_file_attribute_errors():
    with pytest.raises(ValueError) as excinfo:
        ListenerUserAddModifyObject(
            dn="", id="", udm_object_type="", action=ListenerActionEnum.add_mod, object={}, options=[]
        )
    msg = str(excinfo.value)
    assert "Unsupported UDM object type" in msg
    assert 'Missing or empty "school" attribute' in msg
    assert 'Missing "default" in UDM options' in msg

    with pytest.raises(ValueError, match="No UCS@school user object class"):
        ListenerUserAddModifyObject(
            dn="",
            id="",
            udm_object_type="",
            action=ListenerActionEnum.add_mod,
            object={},
            options=["default"],
        )


def test_unknown_school_user_role():
    obj = ListenerUserAddModifyObject(
        dn="",
        id="",
        udm_object_type="users/user",
        action=ListenerActionEnum.add_mod,
        object={"school": "DEMOSCHOOL"},
        options=["default", "ucsschoolStudent"],
    )
    obj.options.remove("ucsschoolStudent")
    with pytest.raises(UnknownSchoolUserRole, match="Unknown or missing school user type in options"):
        _ = obj.school_user_roles
