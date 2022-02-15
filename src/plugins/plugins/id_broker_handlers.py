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

import logging
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
from ldap3.utils.conv import escape_filter_chars

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


async def ping_id_broker(school_authority: SchoolAuthorityConfiguration) -> bool:
    """
    To ping the id-broker side, we try to login and get a token.
    """
    url = urljoin(school_authority.url, "ucsschool/apis/auth/token")
    verify_ssl = "UNSAFE_SSL" not in os.environ
    id_broker_conf = school_authority.plugin_configs["id_broker"]
    payload = {
        "username": id_broker_conf["username"],
        "password": id_broker_conf["password"].get_secret_value(),
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, ssl=verify_ssl, data=payload) as resp:
                if resp.status != 200:
                    return False
        except aiohttp.client_exceptions.ClientConnectorError:
            return False
    return True


async def create_school_if_missing(
    ou: str, ldap_access: LDAPAccess, id_broker_school: IDBrokerSchool, logger: logging.Logger
) -> None:
    entries = await ldap_access.search(
        filter_s=f"(&(objectClass=ucsschoolOrganizationalUnit)(ou={escape_filter_chars(ou)}))",
        attributes=["displayName", "entryUUID"],
    )
    if len(entries) == 1:
        entry_uuid = entries[0].entryUUID.value
        display_name = entries[0].displayName.value
        if not await id_broker_school.exists(entry_uuid):
            logger.info("Creating school %r...", ou)
            await id_broker_school.create(School(id=entry_uuid, name=ou, display_name=display_name))
    else:
        raise IDBrokerNotFoundError(404, f"School {ou!r} does not exist on sender system.")


async def create_class_if_missing(
    school_class: str,
    ou: str,
    ldap_access: LDAPAccess,
    id_broker_school_class: IDBrokerSchoolClass,
    logger: logging.Logger,
) -> None:
    entries = await ldap_access.search(
        filter_s=f"(&(objectClass=univentionGroup)(cn={escape_filter_chars(f'{ou}-{school_class}')}))",
        attributes=["description", "entryUUID"],
    )
    if len(entries) == 1:
        entry_uuid = entries[0].entryUUID.value
        description = entries[0].description.value
        if not await id_broker_school_class.exists(entry_uuid):
            logger.info("Creating school class %r in school %r...", school_class, ou)
            await id_broker_school_class.create(
                SchoolClass(id=entry_uuid, name=ou, description=description, school=ou, members=[])
            )
    else:
        raise IDBrokerNotFoundError(
            404, f"School class {school_class!r} in school {ou!r} does not exist on sender system."
        )


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
        self.id_broker_school_class = IDBrokerSchoolClass(self.school_authority, "id_broker")
        self.id_broker_school = IDBrokerSchool(self.school_authority, "id_broker")
        self.id_broker_user = IDBrokerUser(self.school_authority, "id_broker")
        self.ldap_access = LDAPAccess()

    async def create_or_update_preconditions_met(self, obj: ListenerUserAddModifyObject) -> bool:
        return True

    async def print_ids(self, obj: ListenerUserAddModifyObject) -> None:
        self.logger.info(f"Object that is being created or updated: {obj}")

    async def _handle_attr_context(self, obj: ListenerUserAddModifyObject) -> Dict[str, Any]:
        # Add primary school 1st to context dict (which is always ordered in cpython3). It will then be
        # the 1st in the requests json (at least with the OpenAPI client we're using) and will then
        # hopefully become the primary school at the ID Broker. That is not strictly necessary, as the
        # Self-Disclosure API does not expose that, but it'll be less confusing, when comparing users.
        schools = sorted(obj.schools)
        schools.remove(obj.school)
        schools.insert(0, obj.school)
        context = {
            school_name: {"roles": set(obj.school_user_roles), "classes": set()}
            for school_name in schools
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
        """
        Retrieve a user from ID Broker API.

        If it does not exist on the id broker, we need to raise an UserNotFoundError, so it will be
        created.
        """
        self.logger.debug("Retrieving user with search parameters: %r", search_params)
        try:
            return await self.id_broker_user.get(obj_id=search_params["id"])
        except IDBrokerNotFoundError:
            raise UserNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a user object at the target."""
        for school in sorted(request_body["context"]):
            await create_school_if_missing(school, self.ldap_access, self.id_broker_school, self.logger)
            for school_class in request_body["context"][school]["classes"]:
                await create_class_if_missing(
                    school_class, school, self.ldap_access, self.id_broker_school_class, self.logger
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
        if not await ping_id_broker(school_authority):
            self.logger.error(
                "Failed to call ucsschool-api for school authority API (%s)",
                school_authority.name,
            )
            return False
        self.logger.info(
            "Successfully called ucsschool-api for school authority API (%s)",
            school_authority.name,
        )
        return True


#
# Groups
#


class IDBrokerPerSAGroupDispatcher(PerSchoolAuthorityGroupDispatcherBase):
    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(IDBrokerPerSAGroupDispatcher, self).__init__(school_authority, plugin_name)
        self.attribute_mapping = {
            "id": "id",
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
        return {"school_authority": self.school_authority.name, "id": obj.id}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> SchoolClass:
        """
        Retrieve a school class from ID Broker API.

        :return SchoolClass: school class object on the ID Broker
        :raises GroupNotFoundError: if it does not exist on the ID Broker
        """
        self.logger.debug("Retrieving school class with search parameters: %r", search_params)
        try:
            return await self.id_broker_school_class.get(obj_id=search_params["id"])
        except (IDBrokerNotFoundError, IDBrokerError):
            raise GroupNotFoundError(f"No school class found with search params: {search_params!r}.")

    async def _handle_attr_id(self, obj: ListenerUserAddModifyObject) -> str:
        return obj.id

    async def _handle_attr_school(self, obj: ListenerGroupAddModifyObject) -> str:
        """Name of school for this school class on the target."""
        m = self.class_dn_regex.match(obj.dn)
        return m.groupdict()["ou"]

    async def _handle_attr_users(self, obj: ListenerGroupAddModifyObject) -> List[str]:
        """
        User dns of class have to be entryUUID of the users.
        Hint: In the user plugin the record_uid of the user is set to entryUUID on the id-broker side.
        Here we want to do this again. The record_uid of the user is a different value.
        """
        record_uids = []
        for dn in obj.users:
            user_entries = await self.ldap_access.search(
                base=dn, filter_s="(objectClass=*)", attributes=["entryUUID"]
            )
            if len(user_entries) > 1:
                self.logger.warning(f"Member {dn!r} of group {obj.name!r} was found multiple times.")
            elif len(user_entries) < 1:
                self.logger.warning(f"Member {dn!r} of group {obj.name!r} was not found.")
            else:
                record_uids.append(str(user_entries[0].entryUUID))
        return record_uids

    async def _handle_attr_name(self, obj: ListenerGroupAddModifyObject) -> str:
        """The name should not include the school prefix. It is prepended on the id-broker side."""
        if m := self.class_dn_regex.match(obj.dn):
            school = m.groupdict()["ou"]
            prefix = f"{school}-"
            if obj.name.startswith(prefix):
                return obj.name[len(prefix) :]
        return obj.name

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a school class object at the target."""
        name, school = request_body["name"], request_body["school"]
        self.logger.info(
            "Going to create school class %r in school %r: %r...",
            name,
            school,
            request_body,
        )
        await create_school_if_missing(school, self.ldap_access, self.id_broker_school, self.logger)
        try:
            school_class: SchoolClass = await self.id_broker_school_class.create(
                SchoolClass(**request_body)
            )
            self.logger.info("School class created: %r.", school_class)
        except IDBrokerNotFoundError as exc:
            raise IDBrokerNotFoundError(
                "Provisioning API responded with 'invalid request'."
                " This usually means that a user in the school "
                "class doesn't exist on the server: %s",
                exc,
            )

    async def do_modify(self, request_body: Dict[str, Any], api_school_class_data: SchoolClass) -> None:
        """Modify a school class object at the target."""
        self.logger.info(
            "Going to modify school class %r: %r...",
            api_school_class_data.name,
            request_body,
        )
        name, school = request_body["name"], request_body["school"]
        try:
            await self.id_broker_school_class.update(SchoolClass(**request_body))
            self.logger.info(
                "School class modified: %r  in school %r: %r...",
                name,
                school,
                request_body,
            )
        except IDBrokerNotFoundError as exc:
            raise IDBrokerNotFoundError(
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
        await self.id_broker_school_class.delete(api_school_class_data.id)
        self.logger.info("School class deleted: %r.", api_school_class_data)


class IDBrokerGroupDispatcher(GroupDispatcherPluginBase):
    plugin_name = "id_broker-groups"
    per_s_a_handler_class = IDBrokerPerSAGroupDispatcher

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        if not await ping_id_broker(school_authority):
            self.logger.error(
                "Failed to call ucsschool-api for school authority API (%s)",
                school_authority.name,
            )
            return False
        self.logger.info(
            "Successfully called ucsschool-api for school authority API (%s)",
            school_authority.name,
        )
        return True


plugin_manager.register(IDBrokerUserDispatcher(), IDBrokerUserDispatcher.plugin_name)
plugin_manager.register(IDBrokerGroupDispatcher(), IDBrokerGroupDispatcher.plugin_name)
