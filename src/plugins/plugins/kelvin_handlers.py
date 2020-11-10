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

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector_defaults.output_plugin_handler_base import DispatcherPluginBase
from ucsschool_id_connector_defaults.school_classes_kelvin import KelvinSchoolClassDispatcher
from ucsschool_id_connector_defaults.users_kelvin import KelvinPerSAUserDispatcher, KelvinUserDispatcher


class KelvinHandler(DispatcherPluginBase):
    """
    Send current state of user or group to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSAUserDispatcher` and
    `KelvinPerSAUserDispatcher` instances which handle user and group data for the
    queues school authority.
    """

    plugin_name = "kelvin"
    per_s_a_handler_class = KelvinPerSAUserDispatcher  # only here to fulfill the API

    def __init__(self):
        super(KelvinHandler, self).__init__()
        self.user_handler = KelvinUserDispatcher()
        self.school_class_handler = KelvinSchoolClassDispatcher()

    @hook_impl
    async def shutdown(self) -> None:
        """impl for ucsschool_id_connector.plugins.Preprocessing.shutdown"""
        await self.user_handler.shutdown()
        await self.school_class_handler.shutdown()

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """
        Handles both user and group objects.

        impl for ucsschool_id_connector.plugins.Postprocessing.handle_listener_object
        """
        if isinstance(obj, ListenerUserAddModifyObject) or isinstance(obj, ListenerUserRemoveObject):
            return await self.user_handler.handle_listener_object(school_authority, obj)
        elif isinstance(obj, ListenerGroupAddModifyObject) or isinstance(obj, ListenerGroupRemoveObject):
            return await self.school_class_handler.handle_listener_object(school_authority, obj)
        else:
            return False

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        # doesn't matter which handler is used
        return await self.user_handler.school_authority_ping(school_authority)


plugin_manager.register(KelvinHandler(), KelvinHandler.plugin_name)
