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

import datetime
from unittest.mock import patch

import pytest
from faker import Faker

import ucsschool_id_connector.models as models
from ucsschool.kelvin.client import PasswordsHashes
from ucsschool_id_connector.plugin_loader import load_plugins
from ucsschool_id_connector.plugins import plugin_manager

fake = Faker()


@pytest.fixture
def async_mock_load_school2target_mapping(school2school_authority_mapping):
    async def _func():
        return school2school_authority_mapping()

    return _func


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ("kelvin",))
async def test_map_attributes(
    api,
    mock_plugins,
    listener_user_add_modify_object,
    school_authority_configuration,
    async_mock_load_school2target_mapping,
):
    load_plugins()
    user_handler_class = {
        "kelvin": "KelvinHandler",
    }[api]
    for plugin in plugin_manager.get_plugins():
        if plugin.__class__.__name__ == user_handler_class:
            break
    else:
        raise AssertionError(f"Cannot find handler class for {api!r} API in plugins.")
    s_a_config = {
        "kelvin": school_authority_configuration(),
    }[api]
    # can only be imported after load_plugins():
    import ucsschool_id_connector.config_storage
    from ucsschool_id_connector_defaults.users_kelvin import KelvinPerSAUserDispatcher

    user_handler: KelvinPerSAUserDispatcher = plugin.per_s_a_handler_class(s_a_config, api)
    user_obj: models.ListenerUserAddModifyObject = listener_user_add_modify_object()
    user_handler._school_ids_on_target_cache = dict((ou, fake.uri()) for ou in user_obj.schools)
    user_handler._school_ids_on_target_cache_creation = datetime.datetime.now()
    user_handler._roles_on_target_cache = dict(
        (role.name, fake.uri()) for role in user_obj.school_user_roles
    )

    with patch.object(
        ucsschool_id_connector.config_storage.ConfigurationStorage,
        "load_school2target_mapping",
        async_mock_load_school2target_mapping,
    ):
        res = await user_handler.map_attributes(user_obj, s_a_config.plugin_configs[api]["mapping"])
    school = [ou for ou in user_obj.schools if ou in user_obj.dn][0]
    schools_ids_on_target = await user_handler.schools_ids_on_target
    roles_on_target = await user_handler.roles_on_target
    school_uri = schools_ids_on_target[school]
    exp = {
        "disabled": user_obj.object["disabled"],
        "firstname": user_obj.object["firstname"],
        "lastname": user_obj.object["lastname"],
        "name": user_obj.username,
        "record_uid": user_obj.record_uid,
        "roles": list(roles_on_target.values()),
        "school": school_uri,
        "school_classes": user_obj.object.get("school_classes", {}),
        "schools": list(schools_ids_on_target.values()),
        "source_uid": user_obj.source_uid,
        "udm_properties": {"pwdChangeNextLogin": user_obj.object["pwdChangeNextLogin"]},
    }
    if api == "kelvin":
        kelvin_password_hashes = user_obj.user_passwords.dict_krb5_key_base64_encoded()
        exp["kelvin_password_hashes"] = {
            "krb_5_key": kelvin_password_hashes["krb5Key"],
            "krb5_key_version_number": kelvin_password_hashes["krb5KeyVersionNumber"],
            "samba_nt_password": kelvin_password_hashes["sambaNTPassword"],
            "samba_pwd_last_set": kelvin_password_hashes["sambaPwdLastSet"],
            "user_password": kelvin_password_hashes["userPassword"],
        }
        assert isinstance(res["kelvin_password_hashes"], PasswordsHashes)
        res["kelvin_password_hashes"] = res["kelvin_password_hashes"].as_dict()
    assert res == exp


# TODO: add test for user_handler_base.PerSchoolAuthorityUserDispatcherBase.search_params
