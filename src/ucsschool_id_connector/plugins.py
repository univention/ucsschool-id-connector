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

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pluggy

from ucsschool_id_connector.constants import PLUGIN_NAMESPACE
from ucsschool_id_connector.models import (
    ListenerAddModifyObject,
    ListenerObject,
    ListenerRemoveObject,
    SchoolAuthorityConfiguration,
)

__all__ = ["hook_impl", "plugin_manager", "filter_plugins"]

hook_impl = pluggy.HookimplMarker(PLUGIN_NAMESPACE)
hook_spec = pluggy.HookspecMarker(PLUGIN_NAMESPACE)
plugin_manager = pluggy.PluginManager(PLUGIN_NAMESPACE)


def filter_plugins(hook_name: str, plugins: List[str]) -> Any:
    """
    This function returns a HookCaller containing only the implementations of the specified plugins.
    If the given list is empty, or no specified plugin implements the hook, the default plugin is chosen.

    :param hook_name: The hook to be executed
    :param plugins: The plugins to be filtered for
    :return: A _HookCaller instance that can be used just like plugin_manager.hook.hook_name
    """
    all_hcaller_names = set()
    for plugin_name in plugins:
        hcallers = [
            hcaller.name
            for hcaller in plugin_manager.get_hookcallers(
                plugin_manager.get_plugin(plugin_name)
            )
        ]
        all_hcaller_names.update(hcallers)
    if hook_name not in all_hcaller_names:
        plugins = ["default"]
    plugins_to_remove = [
        plugin
        for plugin in plugin_manager.get_plugins()
        if plugin_manager.get_name(plugin) not in plugins
    ]
    return plugin_manager.subset_hook_caller(hook_name, plugins_to_remove)


# hint:
# @hook_spec  # return a list of results
# @hook_spec(firstresult=True)  # return only 1 (the first) result, not a list


class ListenerObjectHandler:
    """
    Pluggy hook specifications for handling listener files.
    """

    @hook_spec
    def get_listener_object(self, obj_dict: Dict[str, Any]) -> Optional[ListenerObject]:
        """
        Analyse `obj_dict` and return an instance of a subclass of
        `ListenerObject`. If the type cannot by recognized or should be
        handled by the default code, return `None`.

        Multiple `get_listener_object` hook implementations may run, until one
        returns an object. Further implementations will not be executed.

        :param dict obj_dict: dictionary loaded from the appcenter listener
            converters JSON file
        :return: `None` if not recognized, else instance of a subclass of `ListenerObject`
        :rtype: None or ListenerObject
        """

    @hook_spec
    async def save_listener_object(self, obj: ListenerObject, path: Path) -> bool:
        """
        Store `obj` JSON encoded into file at `path`.

        Multiple `get_listener_object` hook implementations may run, until one
        returns `True`. Further implementations will not be executed.

        :param ListenerObject obj: instance of a subclass of `ListenerObject`
        :param Path path: filesystem path to save to
        :return: whether the file was saved (False to let the default plugin handle it)
        :rtype: bool
        :raises ValueError: JSON encoding error
        :raises OSError: (FileNotFoundError etc)
        """


class Preprocessing:
    """
    Pluggy hook specifications for preprocessing ``ListenerObject``
    instances in the in-queue.
    """

    @hook_spec
    async def shutdown(self) -> None:
        """
        Called when the daemon is shutting down. Close database and network
        connections.
        """

    @hook_spec
    async def preprocess_add_mod_object(self, obj: ListenerAddModifyObject) -> bool:
        """
        Preprocessing of create/modify-objects in the in queue.

        For example store data in a DB, that will not be available in the
        delete operation (use it in `preprocess_remove_object()`), because the
        ListenerRemoveObject has no object data, just the objects `id`. Or
        load additional data missing in the `obj.object`. Or if the difference
        to previous add/mod is needed in a modify operation.

        If `obj` was modified and the out queues should see that modification,
        return `True`, so it gets saved to disk.

        All `preprocess_add_mod_object` hook implementations will be executed.

        :param ListenerAddModifyObject obj: instance of a concrete subclass
            of ListenerAddModifyObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """

    @hook_spec
    async def preprocess_remove_object(self, obj: ListenerRemoveObject) -> bool:
        """
        Preprocessing of remove-objects in the in queue.

        For example get the users previous IDs etc from a DB, as the
        ListenerRemoveObject has no object data.

        If `obj` was modified and the out queues should see that modification,
        return `True`, so it gets saved to disk.

        All `preprocess_remove_object` hook implementations will be executed.

        :param ListenerRemoveObject obj: instance of a concrete subclass
            of ListenerRemoveObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """


class Distribution:
    """
    Pluggy hook specifications for preprocessing ``ListenerObject``
    instances in the in-queue.
    """

    @hook_spec
    async def school_authorities_to_distribute_to(
        self, obj: ListenerObject, in_queue
    ) -> Iterable[str]:
        """
        Create list of school authorities this object should be sent to.

        All `school_authorities_to_distribute_to` hook implementations will be
        executed and the result lists will be merged. If the object type cannot
        or should not be handled by the plugin, return an empty list.

        :param ListenerObject obj: of a concrete subclass of ListenerObject
        :param ucsschool_id_connector.queues.InQueue in_queue: the in-queue
        :return: list of names of school authorities, they should match those
            in ``SchoolAuthorityConfiguration.name``
        :rtype: list
        """
        # TODO: currently only passing 'self' (InQueue) because plugins need
        # the 'school_authority_mapping'. Would be better to move that and
        # the related models to a plugin package.


class Postprocessing:
    """
    Pluggy hook specifications for all hooks modifying data in postprocessing.
    The implementations of these hooks need to be registered with a name, since the set of plugins
    executed can be configured for every school authority individually.
    """

    @hook_spec
    async def create_request_kwargs(
        self, http_method: str, url, school_authority: SchoolAuthorityConfiguration
    ) -> Dict[Any, Any]:
        """
        Creates a dictionary the kwargs for the aiohttp request should be updated with.

        The configured ``create_request_kwargs`` hooks for a given school authority will
        be executed. The returned dictionaries are used to update the kwargs for
        aiohttp with. Common use cases would be the addition of headers or authentication
        strategies.
        :param http_method: The HTTP method used, e.g. POST
        :param url: The complete url this request goes to
        :param school_authority: The school authority configuration that this request targets
        :return: The dictionary to update the request kwargs with
        """

    @hook_spec
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """
        This hook is the entry point for the entire handling logic of ``ListenerObjects``
        in the out queue.
        All handler hooks that have been registered and appear in a specific school authority
        configuration are executed.
        If no registered hook handles the object and thus none returned ``True``, an error
        will be logged.
        :param school_authority: The school authority this object is handled for
        :param obj: The ListenerObject to handle
        :return: True if this hook handled the object, otherwise False
        """

    @hook_spec
    async def school_authority_ping(
        self, school_authority: SchoolAuthorityConfiguration
    ) -> bool:
        """
        This hook can be defined to implement a connectivity check to the API of a school authority.
        If any registered ping hooks for a school authority returns ``False``, the communication is
        considered faulty.

        :param school_authority: The school authority to check the connectivity to.
        :return: True if check succeeds, otherwise False
        """


plugin_manager.add_hookspecs(ListenerObjectHandler)
plugin_manager.add_hookspecs(Preprocessing)
plugin_manager.add_hookspecs(Distribution)
plugin_manager.add_hookspecs(Postprocessing)
