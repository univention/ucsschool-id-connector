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
from typing import Any, Dict, Optional

import pluggy

from .constants import PLUGIN_NAMESPACE
from .models import ListenerObject

__all__ = ["hook_impl", "plugin_manager"]

hook_impl = pluggy.HookimplMarker(PLUGIN_NAMESPACE)
hook_spec = pluggy.HookspecMarker(PLUGIN_NAMESPACE)
plugin_manager = pluggy.PluginManager(PLUGIN_NAMESPACE)

# hint:
# @hook_spec  # return a list of results
# @hook_spec(firstresult=True)  # return only 1 (the first) result, not a list


class ListenerObjectHandler:
    @hook_spec  # return a list of results
    def get_listener_object(self, obj_dict: Dict[str, Any]) -> Optional[ListenerObject]:
        """
        Analyse `obj_dict` and return an instance of a subclass of
        `ListenerObject`. If the type cannot by recognized or should be
        handled by the default code, return `None`.

        :param dict obj_dict: dictionary loaded from the appcenter listener
            converters JSON file
        :return: `None` if not recognized, else instance of a subclass of `ListenerObject`
        :rtype: None or ListenerObject
        """

    @hook_spec(firstresult=True)
    def save_listener_object(self, obj: ListenerObject, path: Path) -> bool:
        """
        Store `obj` JSON encoded into file at `path`.

        :param ListenerObject obj: instance of a subclass of `ListenerObject`
        :param Path path: filesystem path to save to
        :return: whether the file was saved (False to let the default plugin handle it)
        :rtype: bool
        :raises ValueError: JSON encoding error
        :raises OSError: (FileNotFoundError etc)
        """


plugin_manager.add_hookspecs(ListenerObjectHandler)
