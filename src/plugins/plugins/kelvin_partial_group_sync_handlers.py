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
from typing import Dict, List

from ucsschool.kelvin.client import NoObject, SchoolClassResource
from ucsschool_id_connector.ldap_access import LDAPAccess
from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.utils import ucsschool_role_regex
from ucsschool_id_connector_defaults.distribution_group_base import GroupDistributionImplBase
from ucsschool_id_connector_defaults.output_plugin_handler_base import DispatcherPluginBase
from ucsschool_id_connector_defaults.school_classes_kelvin import (
    KelvinPerSASchoolClassDispatcher,
    KelvinSchoolClassDispatcher,
)
from ucsschool_id_connector_defaults.users_kelvin import KelvinPerSAUserDispatcher, KelvinUserDispatcher


class KelvinPartialGroupSyncPerSASchoolClassDispatcher(KelvinPerSASchoolClassDispatcher):
    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super().__init__(school_authority, plugin_name)
        self._ldap_access = LDAPAccess()

    async def fetch_roles(self) -> Dict[str, str]:
        """Just here to fullfill the API"""
        return await super().fetch_roles()

    async def _check_user_ignore(self, roles: str) -> bool:
        """
        Checks if any of the given role strings that have a context of any school this
        school authority handles and is configured to be ignored in the plugin configuration.

        :return: True if a role to be ignored was found, False otherwise
        """
        role_pattern = ucsschool_role_regex()
        handled_schools = await self.handled_schools()
        roles_to_ignore = set(
            self.school_authority.plugin_configs[self.plugin_name].get("school_classes_ignore_roles", [])
        )
        role_dicts = [
            match.groupdict() for match in (role_pattern.search(role) for role in roles) if match
        ]
        user_roles = set(
            [
                obj["role"]
                for obj in role_dicts
                if obj["context_type"] == "school" and obj["context"] in handled_schools
            ]
        )
        return not roles_to_ignore.isdisjoint(user_roles)

    async def _get_remote_usernames(self, name: str, school: str) -> List[str]:
        """
        Returns the usernames of all members of the school class specified by name and school
        from the target system.
        """
        try:
            remote_school_class = await SchoolClassResource(session=self.session).get(
                name=name, school=school
            )
            remote_usernames = remote_school_class.users
        except NoObject:
            remote_usernames = []
        return remote_usernames

    async def _handle_attr_users(self, obj: ListenerGroupAddModifyObject) -> List[str]:
        """
        Calculates the new set of members that should be set for the school class
        to be created or modified. The way this is done is documented in the README.md
        """
        school, name = obj.object["name"].split("-")
        local_usernames = await super()._handle_attr_users(obj)
        local_users = [
            await self._ldap_access.get_user(username, attributes=["ucsschoolRole"])
            for username in local_usernames
        ]
        local_ignore_users = [
            user.username
            for user in local_users
            if await self._check_user_ignore(user.attributes.get("ucsschoolRole", []))
        ]

        remote_usernames = await self._get_remote_usernames(name, school)
        remote_users = []
        remote_unkown_usernames = []
        for username in remote_usernames:
            remote_user = await self._ldap_access.get_user(username, attributes=["ucsschoolRole"])
            if remote_user:
                remote_users.append(remote_user)
            else:
                remote_unkown_usernames.append(username)
        remote_keep_users = [
            user.username
            for user in remote_users
            if user and await self._check_user_ignore(user.attributes.get("ucsschoolRole", []))
        ]
        return list(
            (set(local_usernames) - set(local_ignore_users))
            .union(set(remote_keep_users))
            .union(remote_unkown_usernames)
        )


class KelvinPartialGroupSyncSchoolClassDispatcher(KelvinSchoolClassDispatcher):
    """
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSASchoolClassDispatcher` instance
    which handles user data for the queues school authority.
    """

    plugin_name = "kelvin-partial-group-sync"
    per_s_a_handler_class = KelvinPartialGroupSyncPerSASchoolClassDispatcher


class KelvinPartialGroupSyncUserDispatcher(KelvinUserDispatcher):
    """
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSAUserDispatcher` instance
    which handles user data for the queues school authority.
    """

    plugin_name = "kelvin-partial-group-sync"


class KelvinPartialGroupSync(DispatcherPluginBase):
    """
    Send current state of user or group to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSAUserDispatcher` and
    `KelvinPerSAUserDispatcher` instances which handle user and group data for the
    queues school authority.

    This derivate of the kelvin plugin allows to alter the users synced
    with school class changes in order to leave certain user roles untouched.
    """

    plugin_name = "kelvin-partial-group-sync"
    per_s_a_handler_class = KelvinPerSAUserDispatcher  # only here to fulfill the API

    def __init__(self):
        super().__init__()
        self.user_handler = KelvinPartialGroupSyncUserDispatcher()
        self.school_class_handler = KelvinPartialGroupSyncSchoolClassDispatcher()

    @hook_impl
    async def shutdown(self) -> None:
        """impl for ucsschool_id_connector.plugins.Preprocessing.shutdown"""
        await self.user_handler.shutdown()
        await self.school_class_handler.shutdown()

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """
        Handles both user and group objects.

        impl for ucsschool_id_connector.plugins.Postprocessing.handle_listener_object
        """
        if isinstance(obj, ListenerUserAddModifyObject) or isinstance(obj, ListenerUserRemoveObject):
            return await self.user_handler.handle_listener_object(school_authority, obj)
        elif isinstance(obj, ListenerGroupAddModifyObject) or isinstance(obj, ListenerGroupRemoveObject):
            return await self.school_class_handler.handle_listener_object(school_authority, obj)
        else:
            return False

    @hook_impl
    async def school_authority_ping(self, school_authority: SchoolAuthorityConfiguration) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.school_authority_ping"""
        # doesn't matter which handler is used
        return await self.user_handler.school_authority_ping(school_authority)


class KelvinPartialGroupSyncGroupDistribution(GroupDistributionImplBase):
    """Distribute school classes to Kelvin API"""

    plugin_name = "kelvin-partial-group-sync"
    target_api_name = "Kelvin API"


plugin_manager.register(KelvinPartialGroupSync(), KelvinPartialGroupSync.plugin_name)
plugin_manager.register(KelvinPartialGroupSyncGroupDistribution())
