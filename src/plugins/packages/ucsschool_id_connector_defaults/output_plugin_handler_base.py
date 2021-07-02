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

"""
Base classes for plugins handling UDM objects.

When writing a user or group object handler, see `user_handler_base.py` and
`group_handler_base.py`. This module contains their base code and can be used
to write plugins for other object types.

The plugin entry code is in the class `DispatcherPluginBase`.
The "per school authority code" goes into `PerSchoolAuthorityDispatcherBase`.
"""

import abc
import datetime
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar, Union

from async_property import async_property

from ucsschool_id_connector.constants import API_SCHOOL_CACHE_TTL
from ucsschool_id_connector.models import (
    ListenerAddModifyObject,
    ListenerObject,
    ListenerRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl
from ucsschool_id_connector.requests import APICommunicationError
from ucsschool_id_connector.utils import ConsoleAndFileLogging, recursive_dict_update

RemoteObject = Any
AddModifyObject = TypeVar("AddModifyObject", bound=ListenerAddModifyObject)
RemoveObject = TypeVar("RemoveObject", bound=ListenerRemoveObject)


class ConfigurationError(Exception):
    ...


class MissingData(Exception):
    ...


class SkipAttribute(Exception):
    ...


class UniquenessError(Exception):
    ...


class UnknownSchool(Exception):
    def __init__(self, *args, school: str):
        self.school = school
        super().__init__(*args)


class ObjectNotFoundError(Exception):
    ...


class PerSchoolAuthorityDispatcherBase(abc.ABC):
    """
    Base class for plugins handling UDM objects, per school authority code.

    The plugin entry code is in the class `DispatcherPluginBase`.
    """

    # list of attributes required to find a unique object:
    _required_search_params = ()
    object_type_name = ""  # 'User' or 'Group'

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        self.school_authority = school_authority
        self.plugin_name = plugin_name
        # set to school_authority.plugin_configs[plugin_name]["mapping"]["users"] or similar:
        self.attribute_mapping: Dict[str, str] = {}
        self.logger = ConsoleAndFileLogging.get_logger(
            f"{self.__class__.__name__}({self.school_authority.name})"
        )
        self._roles_on_target_cache: Dict[str, str] = {}
        self._school_ids_on_target_cache: Dict[str, str] = {}
        self._school_ids_on_target_cache_creation = datetime.datetime(1970, 1, 1)

    async def handle_create_or_update(self, obj: AddModifyObject) -> None:
        """Create or modify object."""
        self.logger.info("Going to create or update %r.", obj)
        self.logger.debug("*** obj.dict()=%r", obj.dict())
        if not await self.create_or_update_preconditions_met(obj):
            return
        await self.print_ids(obj)
        await self.do_create_or_update(obj)

    async def handle_remove(self, obj: RemoveObject) -> None:
        """Remove object."""
        self.logger.info("Going to remove %r.", obj)
        self.logger.debug("*** obj.dict()=%r", obj.dict())
        if not await self.remove_preconditions_met(obj):
            return
        try:
            exists, api_user_data = await self.exists_on_target(obj)
        except MissingData as exc:
            self.logger.error(str(exc))
            return
        if exists:
            await self.do_remove(obj, api_user_data)
        else:
            self.logger.info(
                "Skipping deletion of %s not found on the target system: %r.", self.object_type_name, obj
            )

    async def create_or_update_preconditions_met(self, obj: AddModifyObject) -> bool:
        """
        Verify preconditions for creating or modifying object on target.
        """
        return True

    async def remove_preconditions_met(self, obj: RemoveObject) -> bool:
        """
        Verify preconditions for removing object on target.
        """
        return True

    async def print_ids(self, obj: AddModifyObject) -> None:
        """
        Print infos about the object to be created/modified.
        """
        pass

    @async_property
    async def schools_ids_on_target(self) -> Dict[str, str]:
        """
        Schools known by the target system dict(name -> ID).

        (ID is in REST APIs usually a URL).
        """
        # update list of school URLs
        if not self._school_ids_on_target_cache or (
            self._school_ids_on_target_cache_creation + datetime.timedelta(seconds=API_SCHOOL_CACHE_TTL)
            < datetime.datetime.now()
        ):
            await self.refresh_schools()
            self._school_ids_on_target_cache_creation = datetime.datetime.now()
        return self._school_ids_on_target_cache

    async def refresh_schools(self):
        self._school_ids_on_target_cache.clear()
        self._school_ids_on_target_cache.update(await self.fetch_schools())
        self.logger.debug(
            "Schools known by API server: %s",
            ", ".join(self._school_ids_on_target_cache.keys()),
        )

    async def fetch_schools(self) -> Dict[str, str]:
        """
        Fetch all schools from API of school authority.

        Something like:
            return dict((school["name"], school["url"]) for school in json_resp["results"])

        :return: dict school name -> url
        """
        raise NotImplementedError()

    @async_property
    async def roles_on_target(self) -> Dict[str, str]:
        """
        Roles known by the target system dict(name -> ID).

        (ID is in REST APIs usually a URL).
        """
        if not self._roles_on_target_cache:
            await self.refresh_roles()
        return self._roles_on_target_cache

    async def refresh_roles(self):
        self._roles_on_target_cache.clear()
        self._roles_on_target_cache.update(await self.fetch_roles())
        self.logger.debug("Roles known by API server: %s", ", ".join(self._roles_on_target_cache.keys()))

    async def fetch_roles(self) -> Dict[str, str]:
        """
        Fetch all roles from API of school authority.

        Something like:
            return dict((role["name"], role["url"]) for role in json_resp["results"])

        :return: dict role name -> url
        """
        raise NotImplementedError()

    async def do_create_or_update(self, obj: AddModifyObject) -> None:
        try:
            request_body = await self.map_attributes(
                obj,
                self.attribute_mapping,
            )
        except Exception as exc:
            self.logger.exception("Mapping attributes: %s", exc)
            raise
        try:
            exists, api_obj_data = await self.exists_on_target(obj)
        except MissingData as exc:
            self.logger.error(str(exc))
            return
        if exists:
            self.logger.info("%s exists on target system, modifying it.", self.object_type_name)
            await self.do_modify(request_body, api_obj_data)
        else:
            self.logger.info("%s does not exist on target system, creating it.", self.object_type_name)
            await self.do_create(request_body)

    async def exists_on_target(
        self, obj: Union[AddModifyObject, RemoveObject]
    ) -> Tuple[bool, Optional[RemoteObject]]:
        """
        Check if the object exists on the school authorities system.

        :param obj: listener object
        :type obj: ListenerAddModifyObject or ListenerRemoveObject
        :return: boolean indicating whether the object exists, and a (possibly
            `None`) object of undefined type that will be passed as-is to
            `do_create` or `do_modify`.
        :rtype: tuple(bool, object)
        :raises MissingData: if data of any attribute in `self._required_search_params`
            is missing or empty on the object
        """
        search_params = await self.search_params(obj)
        for param in self._required_search_params:
            if not search_params.get(param):
                raise MissingData(
                    f"Cannot search for {self.object_type_name}: missing {param} in object:"
                    f" {obj!r} (search_params: {search_params!r})."
                )
        try:
            obj_repr = await self.fetch_obj(search_params)
        except ObjectNotFoundError:
            return False, None
        return True, obj_repr

    async def search_params(self, obj: Union[AddModifyObject, RemoveObject]) -> Dict[str, Any]:
        """
        Usually user objects are searched for using the `entryUUID` or the
        `record_uid` plus the `source_uid`. Group objects are searched using
        their `cn`.

        :param obj: listener object
        :type obj: ListenerAddModifyObject or ListenerRemoveObject
        :return: possible parameters to use in search
        :rtype: dict
        """
        return {"entryUUID": obj.id}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> RemoteObject:
        """
        Retrieve a user from API of school authority.

        :param dict search_params: parameters for search
        :return: representation of user in remote resource
        :rtype: object
        :raises ObjectNotFoundError: if object was not found on the school
            authorities system.
        """
        raise NotImplementedError()

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """
        Create an object object on the target.

        :param dict request_body: output of `map_attributes`
        """
        raise NotImplementedError()

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: RemoteObject) -> None:
        """
        Modify an object object on the target.

        :param dict request_body: output of `map_attributes`
        :param object api_user_data: output of `user_exists_on_target`
        """
        raise NotImplementedError()

    async def do_remove(self, obj: RemoveObject, api_user_data: RemoteObject) -> None:
        """
        Delete an object object on the target.

        Will only be called, if `user_exists_on_target()` returned True.

        :param ListenerUserAddModifyObject obj: user listener object
        :param object api_user_data: output of `user_exists_on_target`
        """
        raise NotImplementedError()

    async def map_attributes(self, obj: AddModifyObject, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Create dict representing the object."""
        res: Dict[str, Any] = {}
        # set attributes configured in mapping
        for key_here, key_there in mapping.items():
            _handle_attr_method_name = f"_handle_attr_{key_here}"
            if hasattr(self, _handle_attr_method_name):
                # handling of special attributes: try using a _handle_attr_* method
                meth: Callable[[AddModifyObject], Any] = getattr(self, _handle_attr_method_name)
                try:
                    value_here = await meth(obj)
                except SkipAttribute:
                    continue
            else:
                # no such method, use value from listener file directly
                value_here = obj.object.get(key_here)

            # `none` may be invalid for the school authorities API
            if value_here is None:
                try:
                    value_here = self._handle_none_value(key_here)
                except SkipAttribute:
                    continue

            recursive_dict_update(res, self._update_for_mapping_data(key_here, key_there, value_here))

        return res

    def _handle_none_value(self, key_here: str) -> Any:
        """
        A target API may have problems with `none` values. Here the value can
        either be changed (return something else) or a `SkipAttribute`
        exception can be raised to not map (send) the attribute at all.
        """
        return None

    def _update_for_mapping_data(self, key_here: str, key_there: str, value_here: Any) -> Dict[str, Any]:
        """
        Structure the data mapping result for the target API.

        For example:

            if key_there in MAIN_ATTRIBUTES:
                return {key_there: value_here}
            else:
                return {"udm_properties": {key_there: value_here}}

        :param key_here: attribute name at sender
        :param key_there: attribute name at receiver
        :param value_here: data to send
        :return: dict that will be used to `update()` the complete data
            mapping dict of `map_attributes`
        """
        return {key_there: value_here}

    async def shutdown(self) -> None:
        """Clean shutdown procedure."""
        pass


PerSchoolAuthorityHandlerBaseObject = TypeVar(
    "PerSchoolAuthorityHandlerBaseObject", bound=PerSchoolAuthorityDispatcherBase
)


class DispatcherPluginBase(abc.ABC):
    """
    Base class for plugins handling UDM objects.

    Send current state of object to target system (school authority).

    Each out queue has its own `HandlerPerSchoolAuthorityBase` instance
    which handles object data for its queues school authority.
    """

    plugin_name = ""
    per_s_a_handler_class: Type[PerSchoolAuthorityHandlerBaseObject] = None  # set this to your class

    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self._per_s_a_handlers: Dict[Tuple[str, str], PerSchoolAuthorityHandlerBaseObject] = dict()

    @hook_impl
    async def shutdown(self) -> None:
        """impl for ucsschool_id_connector.plugins.Preprocessing.shutdown"""
        for handler in self._per_s_a_handlers.values():
            await handler.shutdown()

    @hook_impl
    async def create_request_kwargs(
        self, http_method: str, url: str, school_authority: SchoolAuthorityConfiguration
    ) -> Dict[Any, Any]:
        """impl for ucsschool_id_connector.plugins.Postprocessing.create_request_kwargs"""
        return {}

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.handle_listener_object"""
        raise NotImplementedError()

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        handler = self.handler(school_authority, self.plugin_name)
        try:
            await handler.refresh_roles()
            await handler.refresh_schools()
        except APICommunicationError as exc:
            self.logger.error(
                "Error calling school authority API (%s): %s",
                school_authority.name,
                exc,
            )
            return False
        return True

    def handler(
        self, school_authority: SchoolAuthorityConfiguration, plugin_name: str
    ) -> PerSchoolAuthorityHandlerBaseObject:
        key = (school_authority.name, plugin_name)
        if key not in self._per_s_a_handlers:
            self._per_s_a_handlers[key] = self.per_s_a_handler_class(school_authority, plugin_name)
        return self._per_s_a_handlers[key]
