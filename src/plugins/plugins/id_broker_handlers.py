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

import os
from typing import Any, Dict, List, Union
from urllib.parse import urljoin

import aiohttp
from idbroker.id_broker_client import (
    IDBrokerError,
    IDBrokerNotFoundError,
    IDBrokerSchool,
    IDBrokerSchoolClass,
    IDBrokerUser,
    School,
    SchoolClass,
    User,
)

from ucsschool_id_connector.ldap_access import LDAPAccess
from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.utils import school_class_dn_regex
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


async def ping_open_api_json(school_authority: SchoolAuthorityConfiguration) -> bool:
    """
    To ping the id-broker side, we try to get the openapi.json.
    """
    url = urljoin(school_authority.url, "ucsschool/apis/openapi.json")
    verify_ssl = "UNSAFE_SSL" not in os.environ
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=verify_ssl) as resp:
            if resp.status != 200:
                return False
    return True


#
# Users
#


class IDBrokerPerSAUserDispatcher(PerSchoolAuthorityUserDispatcherBase):

    _required_search_params = ("id",)

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(IDBrokerPerSAUserDispatcher, self).__init__(school_authority, plugin_name)
        self.class_dn_regex = school_class_dn_regex()
        self.attribute_mapping = {
            "id": "id",
            "username": "user_name",
            "firstname": "first_name",
            "lastname": "last_name",
            "context": "context",
        }
        self.id_broker_school = IDBrokerSchool(self.school_authority, "id_broker")
        self.id_broker_user = IDBrokerUser(self.school_authority, "id_broker")
        self.ldap_access = LDAPAccess()

    async def create_or_update_preconditions_met(self, obj: ListenerUserAddModifyObject) -> bool:
        return True

    async def print_ids(self, obj: ListenerUserAddModifyObject) -> None:
        self.logger.info(f"Object that is being created or updated: {obj}")

    async def _handle_attr_context(self, obj: ListenerUserAddModifyObject) -> Dict[str, Any]:
        context = {
            school_name: {"roles": set(obj.school_user_roles), "classes": set()}
            for school_name in obj.schools
        }
        for group_dn in obj.object.get("groups", []):
            if m := self.class_dn_regex.match(group_dn):
                name = m.groupdict()["name"]
                school = m.groupdict()["ou"]
                context[school]["classes"].add(name)
        return context

    async def _handle_attr_id(self, obj: ListenerUserAddModifyObject) -> str:
        return obj.id

    async def search_params(
        self, obj: Union[ListenerUserAddModifyObject, ListenerUserRemoveObject]
    ) -> Dict[str, Any]:
        return {"id": obj.id}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> User:
        """Retrieve a user from ID Broker API.
        If it does not exist on the id broker, we need to
        raise an UserNotFoundError, so it will be created."""
        self.logger.debug("Retrieving user with search parameters: %r", search_params)
        try:
            return await self.id_broker_user.get(user_id=search_params["id"])
        except IDBrokerNotFoundError:
            raise UserNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a user object at the target."""
        for school in request_body["context"]:
            if not await self.id_broker_school.exists(school):
                entries = await self.ldap_access.search(
                    filter_s=f"(ou={school})", attributes=["displayName"]
                )
                if len(entries) == 1:
                    await self.id_broker_school.create(
                        School(name=school, display_name=str(entries[0].displayName))
                    )
                else:
                    raise Exception(
                        f"School {school} of User {request_body['username']}"
                        f" was not found on sender system."
                    )
            self.logger.info(
                "Going to create user %r in school %r: %r...",
                request_body["id"],
                school,
                request_body,
            )
        user: User = await self.id_broker_user.create(User(**request_body))
        self.logger.info("User created: %r.", user)

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: User) -> None:
        """Modify a user object at the target."""
        self.logger.info("Going to modify user %r: %r...", api_user_data.user_name, request_body)
        user: User = await self.id_broker_user.update(User(**request_body))
        self.logger.info("User modified: %r.", user)

    async def do_remove(self, obj: ListenerGroupRemoveObject, api_user_data: User) -> None:
        """Delete a user object at the target."""
        self.logger.info("Going to delete user: %r...", obj)
        await self.id_broker_user.delete(api_user_data.id)
        self.logger.info("User deleted: %r.", api_user_data)


class IDBrokerUserDispatcher(UserDispatcherPluginBase):
    plugin_name = "id_broker-users"
    per_s_a_handler_class = IDBrokerPerSAUserDispatcher

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        if not await ping_open_api_json(school_authority):
            self.logger.error(
                "Failed to call ucsschool-api for school authority API (%s)",
                school_authority.name,
            )
            return False
        return True


#
# Groups
#


class IDBrokerPerSAGroupDispatcher(PerSchoolAuthorityGroupDispatcherBase):
    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(IDBrokerPerSAGroupDispatcher, self).__init__(school_authority, plugin_name)
        self.attribute_mapping = {
            "name": "name",
            "description": "description",
            "school": "school",
            "users": "members",
        }
        self.id_broker_school_class = IDBrokerSchoolClass(self.school_authority, "id_broker")
        self.id_broker_school = IDBrokerSchool(self.school_authority, "id_broker")
        self.class_dn_regex = school_class_dn_regex()
        self.ldap_access = LDAPAccess()

    async def create_or_update_preconditions_met(self, obj: ListenerGroupAddModifyObject) -> bool:
        """Verify preconditions for creating or modifying object on target."""
        return await self.is_schools_class(obj)

    async def remove_preconditions_met(self, obj: ListenerGroupRemoveObject) -> bool:
        """
        Verify preconditions for removing object on target.
        """
        return await self.is_schools_class(obj)

    async def is_schools_class(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ) -> bool:
        """Check if group is a school class."""
        return bool(self.class_dn_regex.match(obj.dn))

    async def search_params(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ) -> Dict[str, Any]:
        m = self.class_dn_regex.match(obj.dn)
        name = m.groupdict()["name"]
        school = m.groupdict()["ou"]
        return {"school_authority": self.school_authority.name, "name": name, "school": school}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> SchoolClass:
        """Retrieve a school class from ID Broker API.
        If it does not exist on the id broker, we need to
        raise an GroupNotFoundError, so it will be created."""
        self.logger.debug("Retrieving school class with search parameters: %r", search_params)
        try:
            return await self.id_broker_school_class.get(
                name=search_params["name"], school=search_params["school"]
            )
        except (IDBrokerNotFoundError, IDBrokerError):
            raise GroupNotFoundError(f"No school class found with search params: {search_params!r}.")

    async def _handle_attr_school(self, obj: ListenerGroupAddModifyObject) -> str:
        """Name of school for this school class on the target."""
        m = self.class_dn_regex.match(obj.dn)
        return m.groupdict()["ou"]

    async def _handle_attr_users(self, obj: ListenerGroupAddModifyObject) -> List[str]:
        """User dns of class have to be entryUUID of the users.
        Hint: In the user plugin the record_uid of the user is set to entryUUID on the id-broker side.
        Here we want to do this again. The record_uid of the user is a different value.
        """
        record_uids = []
        for dn in obj.users:
            user_entries = await self.ldap_access.search(
                base=dn, filter_s="(objectClass=*)", attributes=["entryUUID"]
            )
            if len(user_entries) >= 1:
                if len(user_entries) != 1:
                    self.logger.warning(f"User {dn} was found multiple times.")
                record_uids.append(str(user_entries[0].entryUUID))
        return record_uids

    async def _handle_attr_name(self, obj: ListenerGroupAddModifyObject) -> str:
        """
        The name should not include the school prefix. It is prepended on the
        id-broker side.
        """
        if m := self.class_dn_regex.match(obj.dn):
            school = m.groupdict()["ou"]
            prefix = f"{school}-"
            if obj.name.startswith(prefix):
                return obj.name[len(prefix) :]
            return obj.name

    async def _handle_attr_description(self, obj: ListenerGroupAddModifyObject) -> str:
        return "" if not hasattr(obj, "description") else obj.description

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a school class object at the target."""
        name, school = request_body["name"], request_body["school"]
        self.logger.info(
            "Going to create school class %r in school %r: %r...",
            name,
            school,
            request_body,
        )
        if not await self.id_broker_school.exists(school):
            entries = await self.ldap_access.search(
                filter_s=f"(ou={school})", attributes=["displayName"]
            )
            if len(entries) == 1:
                await self.id_broker_school.create(
                    School(name=school, display_name=str(entries[0].displayName))
                )
            else:
                raise Exception(
                    f"School {school} of School class {request_body['name']}"
                    f" was not found on sender system."
                )
        try:
            school_class: SchoolClass = await self.id_broker_school_class.create(
                SchoolClass(**request_body)
            )
            self.logger.info("School class created: %r.", school_class)
        except IDBrokerNotFoundError as exc:
            self.logger.error(
                "Provisioning API responded with 'invalid request'."
                " This usually means that a user in the school "
                "class doesn't exist on the server: %s",
                exc,
            )

    async def do_modify(self, request_body: Dict[str, Any], api_school_class_data: SchoolClass) -> None:
        """Modify a school class object at the target."""
        self.logger.info(
            "Going to modify school class %r: %r...", api_school_class_data.name, request_body
        )
        name, school = request_body["name"], request_body["school"]
        try:
            await self.id_broker_school_class.update(SchoolClass(**request_body))
            self.logger.info(
                "School class modified: %r  in school %r: %r...", name, school, request_body
            )
        except IDBrokerNotFoundError as exc:
            self.logger.error(
                "Provisioning API responded with 'invalid request'."
                " This usually means that a user in the school "
                "class doesn't exist on the server: %s",
                exc,
            )

    async def do_remove(
        self, obj: ListenerGroupRemoveObject, api_school_class_data: SchoolClass
    ) -> None:
        """Delete a school class object at the target."""
        self.logger.info("Going to delete school class: %r...", obj)
        await self.id_broker_school_class.delete(
            api_school_class_data.name, api_school_class_data.school
        )
        self.logger.info("School class deleted: %r.", api_school_class_data)


class IDBrokerGroupDispatcher(GroupDispatcherPluginBase):
    plugin_name = "id_broker-groups"
    per_s_a_handler_class = IDBrokerPerSAGroupDispatcher

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        if not await ping_open_api_json(school_authority):
            self.logger.error(
                "Failed to call ucsschool-api for school authority API (%s)",
                school_authority.name,
            )
            return False
        return True


plugin_manager.register(IDBrokerUserDispatcher(), IDBrokerUserDispatcher.plugin_name)
plugin_manager.register(IDBrokerGroupDispatcher(), IDBrokerGroupDispatcher.plugin_name)
