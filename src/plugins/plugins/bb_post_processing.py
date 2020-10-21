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
from typing import Any, Dict

from ucsschool_id_connector.constants import LOG_FILE_PATH_QUEUES
from ucsschool_id_connector.models import (
    ListenerObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.requests import APICommunicationError
from ucsschool_id_connector.user_handler import UserHandler
from ucsschool_id_connector.utils import ConsoleAndFileLogging


class DefaultPlugin:
    """
    This is the default implementation of the Postprocessing hooks. Currently
    it is targeting the BB-API.
    In the future this entire implementation will be changed to the Kelvin API.
    """

    def __init__(self):
        self._user_handler_cache: Dict[str, UserHandler] = dict()
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__, LOG_FILE_PATH_QUEUES)

    def _get_user_handler(self, school_authority: SchoolAuthorityConfiguration) -> UserHandler:
        if result := self._user_handler_cache.get(school_authority.name):
            return result
        else:
            self._user_handler_cache[school_authority.name] = UserHandler(school_authority)
            return self._user_handler_cache[school_authority.name]

    @hook_impl
    async def shutdown(self) -> None:
        for user_handler in self._user_handler_cache.values():
            await user_handler.shutdown()

    @hook_impl
    async def create_request_kwargs(self, http_method: str, url, school_authority) -> Dict[Any, Any]:
        result = dict()
        result["headers"] = {"Authorization": f"Token {school_authority.password.get_secret_value()}"}
        return result

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        user_handler = self._get_user_handler(school_authority)
        if isinstance(obj, ListenerUserAddModifyObject):
            await user_handler.handle_create_or_update(obj)
        elif isinstance(obj, ListenerUserRemoveObject):
            await user_handler.handle_remove(obj)
        else:
            return False
        return True

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        user_handler = self._get_user_handler(school_authority)
        await user_handler.fetch_roles()
        try:
            self.logger.debug(
                "Roles known by API server (%s): %s",
                school_authority.name,
                ", ".join(user_handler.api_roles_cache.keys()),
            )
            await user_handler.fetch_schools()
            self.logger.debug(
                "Schools known by API server (%s): %s",
                school_authority.name,
                ", ".join((await user_handler.api_schools_cache).keys()),
            )

        except APICommunicationError as exc:
            self.logger.error(
                "Error calling school authority API (%s): %s",
                school_authority.name,
                exc,
            )
            return False
        return True


plugin_manager.register(DefaultPlugin(), "default")
