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

"""
Base classes for plugins handling group objects.

The plugin entry code is in the class `GroupDispatcherPluginBase`.
The "per school authority code" goes into `PerSchoolAuthorityGroupDispatcherBase`.

To implement a UCS@school ID connector plugin :

1. subclass both `GroupDispatcherPluginBase` and `PerSchoolAuthorityGroupDispatcherBase`
2. set `GroupDispatcherPluginBase.plugin_name` to the name used in the school
   authority `plugins_config`
3. set `GroupDispatcherPluginBase.per_s_a_handler_class` to your subclass of
   `PerSchoolAuthorityGroupDispatcherBase`
4. import `from ucsschool_id_connector.plugins import plugin_manager` and at
   the bottom of your plugin module write:
   `plugin_manager.register(MyGroupHandler(), MyGroupHandler.plugin_name)
"""

import abc
from typing import Any, Dict, Type, TypeVar, Union

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl

from .output_plugin_handler_base import (
    DispatcherPluginBase,
    ObjectNotFoundError,
    PerSchoolAuthorityDispatcherBase,
    RemoteObject,
)

RemoteGroup = TypeVar("RemoteGroup", bound=RemoteObject)


class GroupNotFoundError(ObjectNotFoundError):
    ...


class PerSchoolAuthorityGroupDispatcherBase(PerSchoolAuthorityDispatcherBase, abc.ABC):
    """
    Base class for plugins handling group objects, per school authority code.

    The plugin entry code is in the class `GroupDispatcherPluginBase`.
    """

    _required_search_params = ("name",)
    object_type_name = "Group"

    async def search_params(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ) -> Dict[str, Any]:
        """
        Usually the group is searched for using the `entryUUID` or the
        `name` and the `school`.

        :param obj: group listener object
        :type obj: ListenerGroupAddModifyObject or ListenerGroupRemoveObject
        :return: possible parameters to use in search, currently `entryUUID´,
            and `name`
        :rtype: dict
        """
        params = await super(PerSchoolAuthorityGroupDispatcherBase, self).search_params(obj)
        if isinstance(obj, ListenerGroupAddModifyObject):
            # add or modify
            params["name"] = obj.name
        if obj.old_data:
            # modify or delete
            params["name"] = obj.dn.split(",")[0].split("=")[1]
        return params


class GroupDispatcherPluginBase(DispatcherPluginBase, abc.ABC):
    """
    Base class for plugins handling group objects.

    Send current state of group to target system (school authority).

    Each out queue has its own `GroupHandlerPerSchoolAuthorityBase` instance
    which handles group data for its queues school authority.
    """

    per_s_a_handler_class: Type[PerSchoolAuthorityGroupDispatcherBase] = None  # set this to your class

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.handle_listener_object"""
        if isinstance(obj, ListenerGroupAddModifyObject):
            await self.handler(school_authority, self.plugin_name).handle_create_or_update(obj)
        elif isinstance(obj, ListenerGroupRemoveObject):
            await self.handler(school_authority, self.plugin_name).handle_remove(obj)
        else:
            return False
        return True
