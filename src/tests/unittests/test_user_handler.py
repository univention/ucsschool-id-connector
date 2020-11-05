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

import pytest
from faker import Faker

import ucsschool_id_connector.models as models
from ucsschool_id_connector.plugin_loader import load_plugins
from ucsschool_id_connector.plugins import plugin_manager

fake = Faker()

HANDLER_CLASS = "BBUserDispatcher"


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ("bb", "kelvin"))
async def test_map_attributes(
    api,
    mock_plugins,
    listener_user_add_modify_object,
    bb_school_authority_configuration,
    kelvin_school_authority_configuration,
):
    load_plugins()
    for plugin in plugin_manager.get_plugins():
        if plugin.__class__.__name__ == HANDLER_CLASS:
            break
    else:
        raise AssertionError(f"Cannot find {HANDLER_CLASS!r} class in plugins.")
    s_a_config = {
        "bb": bb_school_authority_configuration(),
        "kelvin": kelvin_school_authority_configuration(),
    }[api]
    user_handler = plugin.per_s_a_handler_class(s_a_config, api)
    user_obj: models.ListenerUserAddModifyObject = listener_user_add_modify_object()
    user_handler._school_ids_on_target_cache = dict((ou, fake.uri()) for ou in user_obj.schools)
    user_handler._school_ids_on_target_cache_creation = datetime.datetime.now()
    user_handler._roles_on_target_cache = dict(
        (role.name, fake.uri()) for role in user_obj.school_user_roles
    )

    res = await user_handler.map_attributes(user_obj, s_a_config.plugin_configs[api]["mapping"]["users"])
    school = [ou for ou in user_obj.schools if ou in user_obj.dn][0]
    schools_ids_on_target = await user_handler.schools_ids_on_target
    roles_on_target = await user_handler.roles_on_target
    school_uri = schools_ids_on_target[school]
    assert res == {
        "disabled": user_obj.object["disabled"] == "1",
        "firstname": user_obj.object["firstname"],
        "lastname": user_obj.object["lastname"],
        "name": user_obj.username,
        "record_uid": user_obj.record_uid,
        "roles": list(roles_on_target.values()),
        "school": school_uri,
        "school_classes": user_obj.object.get("school_classes", {}),
        "schools": list(schools_ids_on_target.values()),
        "source_uid": user_obj.source_uid,
        "udm_properties": {
            "ucsschool_id_connector_pw": {
                "krb5Key": [k.decode() for k in user_obj.user_passwords.krb5Key],
                "krb5KeyVersionNumber": user_obj.user_passwords.krb5KeyVersionNumber,
                "sambaNTPassword": user_obj.user_passwords.sambaNTPassword,
                "sambaPwdLastSet": user_obj.user_passwords.sambaPwdLastSet,
                "userPassword": user_obj.user_passwords.userPassword,
            }
        },
    }


# TODO: add test for user_handler_base.PerSchoolAuthorityUserDispatcherBase.search_params
