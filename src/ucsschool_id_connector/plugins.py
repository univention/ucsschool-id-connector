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
from typing import Any, Dict, Iterable, Optional

import pluggy

from .constants import PLUGIN_NAMESPACE
from .models import ListenerAddModifyObject, ListenerObject, ListenerRemoveObject

__all__ = ["hook_impl", "plugin_manager"]

hook_impl = pluggy.HookimplMarker(PLUGIN_NAMESPACE)
hook_spec = pluggy.HookspecMarker(PLUGIN_NAMESPACE)
plugin_manager = pluggy.PluginManager(PLUGIN_NAMESPACE)

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
    def shutdown(self) -> None:
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
        self, obj: ListenerObject, in_queue: "ucsschool_id_connector.queues.InQueue"
    ) -> Iterable[str]:
        """
        Create list of school authorities this object should be sent to.

        All `school_authorities_to_distribute_to` hook implementations will be
        executed and the result lists will be merged. If the object type cannot
        or should not be handled by the plugin, return an empty list.

        :param ListenerObject obj: of a concrete subclass of ListenerObject
        :param InQueue in_queue: the in-queue
        :return: list of names of school authorities, they should match those
            in ``SchoolAuthorityConfiguration.name``
        :rtype: list
        """
        # TODO: currently only passing 'self' (InQueue) because plugins need
        # the 'school_authority_mapping'. Would be better to move that and
        # the related models to a plugin package.


plugin_manager.add_hookspecs(ListenerObjectHandler)
plugin_manager.add_hookspecs(Preprocessing)
plugin_manager.add_hookspecs(Distribution)
