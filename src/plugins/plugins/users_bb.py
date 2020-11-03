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

from typing import Any, Dict, List, Union, cast

import aiohttp

from ucsschool_id_connector.constants import HTTP_CLIENT_TIMEOUT
from ucsschool_id_connector.models import (
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.requests import http_delete, http_get, http_patch, http_post
from ucsschool_id_connector_defaults.user_handler_base import (
    PerSchoolAuthorityUserHandlerBase,
    SkipAttribute,
    UserHandlerPluginBase,
    UserNotFoundError,
)

BB_API_MAIN_ATTRIBUTES = {
    "name",
    "birthday",
    "disabled",
    "email",
    "firstname",
    "lastname",
    "password",
    "record_uid",
    "roles",
    "school",
    "school_classes",
    "schools",
    "source_uid",
    "ucsschool_roles",
}

UserObject = Dict[str, Any]


class MissingData(Exception):
    ...


class BBPerSAUserHandler(PerSchoolAuthorityUserHandlerBase):
    """
    THIS CLASS IS DEPRECATED AND WILL BE REMOVED IN FUTURE VERSIONS OF THE
    CONNECTOR THAT TARGETS KELVIN AS THE DEFAULT API.

    BB plugin handling user objects, per school authority code.
    """

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(BBPerSAUserHandler, self).__init__(school_authority, plugin_name)
        timeout = aiohttp.ClientTimeout(total=HTTP_CLIENT_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def handle_create_or_update(self, obj: ListenerUserAddModifyObject) -> None:
        """Create or modify user."""
        # TODO: create HTTP resource to make server reload the OUs
        # for now be very inefficient and force a fetch_schools() for every user!:
        self._school_ids_on_target_cache.clear()
        await super(BBPerSAUserHandler, self).handle_create_or_update(obj)

    async def handle_remove(self, obj: ListenerUserRemoveObject) -> None:
        """Remove user."""
        # TODO: create HTTP resource to make server reload the OUs
        # for now be very inefficient and force a fetch_schools() for every user!:
        self._school_ids_on_target_cache.clear()
        await super(BBPerSAUserHandler, self).handle_remove(obj)

    async def fetch_roles(self) -> Dict[str, str]:
        """Fetch all roles from API of school authority."""
        url = f"{self.school_authority.url}/roles/"
        status, json_resp = await http_get(url, self.school_authority, session=self._session)
        return dict((role["name"], role["url"]) for role in json_resp["results"])

    async def fetch_schools(self) -> Dict[str, str]:
        """Fetch all schools from API of school authority."""
        url = f"{self.school_authority.url}/schools/"
        status, json_resp = await http_get(url, self.school_authority, session=self._session)
        return dict((school["name"], school["url"]) for school in json_resp["results"])

    async def user_search_params(
        self, obj: Union[ListenerUserAddModifyObject, ListenerUserRemoveObject]
    ) -> Dict[str, Any]:
        res = await super(BBPerSAUserHandler, self).user_search_params(obj)
        # filter out unwanted search parameters
        return {
            "record_uid": res["record_uid"],
            "source_uid": res["source_uid"],
        }

    async def fetch_user(self, search_params: Dict[str, Any]) -> UserObject:
        """Retrieve a user from API of school authority."""
        url = f"{self.school_authority.url}/users/"
        status, json_resp = await http_get(
            url, self.school_authority, search_params, session=self._session
        )
        json_resp = cast(List[Dict[Any, Any]], json_resp)
        self.logger.debug("status=%r json_resp=%r", status, json_resp)
        if json_resp:
            return json_resp[0]
        else:
            raise UserNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a user object at the target."""
        status, json_resp = await http_post(
            f"{self.school_authority.url}/users/",
            self.school_authority,
            session=self._session,
            data=request_body,
        )
        self.logger.info("User created (status: %r): %r", status, json_resp)

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: UserObject) -> None:
        """Modify a user object at the target."""
        status, json_resp = await http_patch(
            api_user_data["url"], self.school_authority, session=self._session, data=request_body
        )
        self.logger.info("User modified (status: %r): %r", status, json_resp)

    async def do_remove(self, obj: ListenerUserRemoveObject, api_user_data: UserObject) -> None:
        """Delete a user object at the target."""
        status, json_resp = await http_delete(
            api_user_data["url"], self.school_authority, session=self._session
        )
        if status == 204:
            self.logger.info("User deleted (status: %r): %r", status, json_resp)
        else:
            self.logger.error("Deleting user (status: %r): %r", status, json_resp)

    def _handle_none_value(self, key_here: str) -> Any:
        """`none` is mostly invalid for the school authorities API"""
        raise SkipAttribute()

    def _update_for_mapping_data(self, key_here: str, key_there: str, value_here: Any) -> Dict[str, Any]:
        """Structure the data mapping result for the target API."""
        if key_there in BB_API_MAIN_ATTRIBUTES:
            return {key_there: value_here}
        else:
            return {"udm_properties": {key_there: value_here}}

    def _handle_password_hashes(self, obj: ListenerUserAddModifyObject) -> Dict[str, Any]:
        """If password hashed should be sent, return them here."""
        passwords_target_attribute_name = self.school_authority.plugin_configs[self.plugin_name].get(
            "passwords_target_attribute"
        )
        if passwords_target_attribute_name and obj.user_passwords:
            pw_hashes = obj.user_passwords.dict()
            # hashes are already base64 encoded by inqueue->prepare->save
            # but have been made bytes by the pydantic Model definition
            pw_hashes["krb5Key"] = [k.decode("ascii") for k in pw_hashes["krb5Key"]]
            return {"udm_properties": {passwords_target_attribute_name: pw_hashes}}

    async def shutdown(self) -> None:
        await self._session.close()


class BBUserHandler(UserHandlerPluginBase):
    """
    THIS CLASS IS DEPRECATED AND WILL BE REMOVED IN FUTURE VERSIONS OF THE
    CONNECTOR THAT TARGETS KELVIN AS THE DEFAULT API.

    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`BBPerSAUserHandler` instance which
    handles user data for the queues school authority.
    """

    plugin_name = "bb"
    user_handler_class = BBPerSAUserHandler

    @hook_impl
    async def create_request_kwargs(
        self, http_method: str, url: str, school_authority: SchoolAuthorityConfiguration
    ) -> Dict[Any, Any]:
        """impl for ucsschool_id_connector.plugins.Postprocessing.create_request_kwargs"""
        result = await super(BBUserHandler, self).create_request_kwargs(
            http_method, url, school_authority
        )
        result["headers"] = {
            "Authorization": f"Token "
            f"{school_authority.plugin_configs['bb']['token'].get_secret_value()}"
        }
        return result


plugin_manager.register(BBUserHandler(), BBUserHandler.plugin_name)
