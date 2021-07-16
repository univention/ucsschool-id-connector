# -*- coding: utf-8 -*-

# Copyright 2021 Univention GmbH
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

from typing import Any, Dict, Union

from ucsschool.kelvin.client import NoObject

from idbroker.id_broker_client import (
    IDBrokerNotFoundError,
    IDBrokerSchool,
    IDBrokerSchoolClass,
    IDBrokerUser,
    School,
    SchoolClass,
    User,
)

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import plugin_manager, hook_impl
from ucsschool_id_connector.requests import APICommunicationError
from ucsschool_id_connector.utils import lehrer_ou_dn_regex, school_class_dn_regex, schueler_ou_dn_regex
from ucsschool_id_connector_defaults.group_handler_base import (
    GroupDispatcherPluginBase,
    GroupNotFoundError,
    PerSchoolAuthorityGroupDispatcherBase,
)
from ucsschool_id_connector_defaults.user_handler_base import (
    PerSchoolAuthorityUserDispatcherBase,
    UserDispatcherPluginBase,
    UserNotFoundError,
)

#
# Users
#


class IDBrokerPerSAUserDispatcher(PerSchoolAuthorityUserDispatcherBase):
    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(IDBrokerPerSAUserDispatcher, self).__init__(school_authority, plugin_name)
        self.attribute_mapping = {
            "entryUUID": "id",  # todo
            "username": "user_name",
            "first_name": "first_name",
            "lastname": "last_name",
            "": "context",  # todo
        }
        self.id_broker_school = IDBrokerSchool(self.school_authority, "id_broker")
        self.id_broker_user = IDBrokerUser(self.school_authority, "id_broker")
        # todo do we still need this?
        self.s_a_name = school_authority.plugin_configs[plugin_name]["tenant"]

    async def fetch_schools(self) -> Dict[str, str]:
        pass

    async def school_exists(self, name: str) -> bool:
        # todo can we refactor this?
        return await self.id_broker_school.exists(name)

    async def user_exists(self, name: str, school: str) -> bool:
        return await self.id_broker_sc.exists(name, school)

    async def create_school(self, name: str) -> School:
        return await self.id_broker_school.create(name)

    async def create_user(self, attrs: Dict[str, Any]) -> User:
        return await self.id_broker_user.create(attrs)

    async def modify_user(self, id: str, attrs: Dict[str, Any]) -> User:
        return await self.id_broker_user.modify(id, attrs)

    async def delete_user(self, id: str) -> None:
        await self.id_broker_user.delete(id)

    async def search_params(
        self, obj: Union[ListenerUserAddModifyObject, ListenerUserRemoveObject]
    ) -> Dict[str, Any]:
        return {"school_authority": self.school_authority.name, "id": obj.id}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> User:
        """Retrieve a user from ID Broker API."""
        self.logger.debug("Retrieving school class with search parameters: %r", search_params)
        try:
            return await self.id_broker_user.get(id=search_params["id"])
        except IDBrokerNotFoundError:
            raise UserNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a user object at the target."""
        name, school = request_body["name"], request_body["ou"]
        self.logger.info(
            "Going to create school class %r in school %r: %r...",
            request_body["id"],
            request_body["ou"],
            request_body,
        )
        if not self.id_broker_school.exists(school):
            await self.id_broker_school.create(school)
        # todo check this feels wrong - do we really need the create* delete* methods?
        school_class = await self.create_user(**request_body)
        self.logger.info("School class created: %r.", school_class)

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: SchoolClass) -> None:
        """Modify a user object at the target."""
        self.logger.info("Going to modify user %r: %r...", api_user_data.name, request_body)
        school_class: SchoolClass = await self.modify_user(id=request_body["id"], **request_body)
        self.logger.info("User modified: %r.", school_class)

    async def do_remove(self, obj: ListenerGroupRemoveObject, api_user_data: SchoolClass) -> None:
        """Delete a user object at the target."""
        self.logger.info("Going to delete user: %r...", obj)
        await self.delete_user(id=api_user_data.id)
        # self.logger.info("User deleted: %r.", school_class)


class IDBrokerUserDispatcher(UserDispatcherPluginBase):
    plugin_name = "id_broker-users"
    per_s_a_handler_class = IDBrokerPerSAUserDispatcher

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        handler = self.handler(school_authority, self.plugin_name)
        try:
            await handler.refresh_schools()
        except APICommunicationError as exc:
            self.logger.error(
                "Error calling school authority API (%s): %s",
                school_authority.name,
                exc,
            )
            return False
        return True


#
# Groups
#


# class IDBrokerPerSAGroupDispatcher(PerSchoolAuthorityGroupDispatcherBase):
#     def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
#         super(IDBrokerPerSAGroupDispatcher, self).__init__(school_authority, plugin_name)
#         self.attribute_mapping = {
#             "name": "name",
#             "description": "description",
#             "school": "school",
#             "users": "members",
#         }
#         self.id_broker_school_class = IDBrokerSchoolClass(self.school_authority, "id_broker")
#         self.id_broker_school = IDBrokerSchool(self.school_authority, "id_broker")
#         # todo do we still need this?
#         self.s_a_name = school_authority.plugin_configs[plugin_name]["tenant"]
#         self.class_dn_regex = school_class_dn_regex()
#
#     async def create_or_update_preconditions_met(self, obj: ListenerGroupAddModifyObject) -> bool:
#         """Verify preconditions for creating or modifying object on target."""
#         return await self.is_schools_class(obj)
#
#     async def remove_preconditions_met(self, obj: ListenerGroupRemoveObject) -> bool:
#         """
#         Verify preconditions for removing object on target.
#         """
#         return await self.is_schools_class(obj)
#
#     async def is_schools_class(
#         self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
#     ) -> bool:
#         """Check if group is a school class."""
#         return bool(self.class_dn_regex.match(obj.dn))
#
#     async def school_exists(self, name: str) -> bool:
#         return await self.id_broker_school.exists(name)
#
#     async def school_class_exists(self, name: str, school: str) -> bool:
#         return await self.id_broker_school_class.exists(name, school)
#
#     async def create_school(self, name: str) -> School:
#         return await self.id_broker_school.create(name)
#
#     async def create_school_class(self, name: str, school: str, attrs: Dict[str, Any]) -> SchoolClass:
#         return await self.id_broker_school_class.create(name, school, attrs)
#
#     async def modify_school_class(self, name: str, school: str, attrs: Dict[str, Any]) -> SchoolClass:
#         return await self.id_broker_school_class.modify(name, school, attr, attrs)
#
#     async def delete_school_class(self, name: str, school: str) -> None:
#         await self.id_broker_school_class.delete(name, school)
#
#     async def search_params(
#         self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
#     ) -> Dict[str, Any]:
#         m = self.class_dn_regex.match(obj.dn)
#         name = m.groupdict()["name"]
#         school = m.groupdict()["ou"]
#         return {"school_authority": self.school_authority.name, "name": name, "school": school}
#
#     async def fetch_obj(self, search_params: Dict[str, Any]) -> SchoolClass:
#         """Retrieve a school class from ID Broker API."""
#         self.logger.debug("Retrieving school class with search parameters: %r", search_params)
#         try:
#             return await self.id_broker_school_class.get(
#                 name=search_params["name"], school=search_params["school"]
#             )
#         except IDBrokerNotFoundError:
#             raise GroupNotFoundError(f"No school class found with search params: {search_params!r}.")
#
#     async def _handle_attr_school(self, obj: ListenerGroupAddModifyObject) -> str:
#         """Name of school for this school class on the target."""
#         m = self.class_dn_regex.match(obj.dn)
#         return m.groupdict()["ou"]
#
#     async def do_create(self, request_body: Dict[str, Any]) -> None:
#         """Create a school class object at the target."""
#         name, school = request_body["name"], request_body["ou"]
#         self.logger.info(
#             "Going to create school class %r in school %r: %r...",
#             request_body["name"],
#             request_body["ou"],
#             request_body,
#         )
#         if not self.id_broker_school.exists(school):
#             self.id_broker_school.create(school)
#         try:
#             # todo check this feels wrong - do we really need the create* delete* methods?
#             school_class = await self.create_school_class(name=name, school=school, **request_body)
#             self.logger.info("School class created: %r.", school_class)
#         except NoObject as exc:
#             self.logger.error(
#                 "Kelvin API responded with 'no object'. This usually means that a user in the school "
#                 "class doesn't exist on the server: %s",
#                 exc,
#             )
#
#     async def do_modify(self, request_body: Dict[str, Any], api_user_data: SchoolClass) -> None:
#         """Modify a school class object at the target."""
#         self.logger.info("Going to modify school class %r: %r...", api_user_data.name, request_body)
#         try:
#             school_class: SchoolClass = await self.modify_school_class(
#                 school=request_body["ou"], name=request_body["name"], **request_body
#             )
#             self.logger.info("School class modified: %r.", school_class)
#         except NoObject as exc:
#             self.logger.error(
#                 "Kelvin API responded with 'no object'. This usually means that a user in the school "
#                 "class doesn't exist on the server: %s",
#                 exc,
#             )
#
#     async def do_remove(self, obj: ListenerGroupRemoveObject, api_user_data: SchoolClass) -> None:
#         """Delete a school class object at the target."""
#         self.logger.info("Going to delete school class: %r...", obj)
#         await self.delete_school_class(name=api_user_data.name, school=api_user_data.school)
#         self.logger.info("School class deleted: %r.", api_user_data)
#
#
# class IDBrokerGroupDispatcher(GroupDispatcherPluginBase):
#     plugin_name = "idbroker-groups"
#     per_s_a_handler_class = IDBrokerPerSAGroupDispatcher


plugin_manager.register(IDBrokerUserDispatcher(), IDBrokerUserDispatcher.plugin_name)
# plugin_manager.register(IDBrokerGroupDispatcher(), IDBrokerGroupDispatcher.plugin_name)
