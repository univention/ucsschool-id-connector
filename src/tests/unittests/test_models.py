# -*- coding: utf-8 -*-

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

from pydantic import SecretStr

from ucsschool_id_connector.models import SchoolAuthorityConfiguration


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


def test_school_authority_configuration_as_dict_pw_is_str(
    school_authority_configuration,
):
    sac: SchoolAuthorityConfiguration = school_authority_configuration()
    assert isinstance(sac.plugin_configs["kelvin"]["password"], SecretStr)
    password = sac.plugin_configs["kelvin"]["password"].get_secret_value()
    sac_as_dict_with_pw_as_str = sac.dict_secrets_as_str()
    assert isinstance(sac_as_dict_with_pw_as_str["plugin_configs"]["kelvin"]["password"], str)
    assert sac_as_dict_with_pw_as_str["plugin_configs"]["kelvin"]["password"] == password
