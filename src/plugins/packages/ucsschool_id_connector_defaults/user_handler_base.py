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
Base classes for plugins handling user objects.

The plugin entry code is in the class `UserDispatcherPluginBase`.
The "per school authority code" goes into `PerSchoolAuthorityUserDispatcherBase`.

To implement a UCS@school ID connector plugin :

1. subclass both `UserDispatcherPluginBase` and `PerSchoolAuthorityUserDispatcherBase`
2. set `UserDispatcherPluginBase.plugin_name` to the name used in the school
   authority `plugins_config`
3. set `UserDispatcherPluginBase.per_s_a_handler_class` to your subclass of
   `PerSchoolAuthorityUserDispatcherBase`
4. import `from ucsschool_id_connector.plugins import plugin_manager` and at
   the bottom of your plugin module write:
   `plugin_manager.register(MyUserHandler(), MyUserHandler.plugin_name)
"""

import abc
import datetime
import random
import string
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from ucsschool_id_connector.models import (
    ListenerActionEnum,
    ListenerObject,
    ListenerUserAddModifyObject,
    ListenerUserOldDataEntry,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
    SchoolUserRole,
    UnknownSchoolUserRole,
    UserPasswords,
)
from ucsschool_id_connector.plugins import hook_impl
from ucsschool_id_connector.utils import get_source_uid, recursive_dict_update, school_class_dn_regex

from .output_plugin_handler_base import (
    DispatcherPluginBase,
    ObjectNotFoundError,
    PerSchoolAuthorityDispatcherBase,
    RemoteObject,
    UnknownSchool,
)

RemoteUser = TypeVar("RemoteUser", bound=RemoteObject)


class UserNotFoundError(ObjectNotFoundError):
    ...


class PerSchoolAuthorityUserDispatcherBase(PerSchoolAuthorityDispatcherBase, abc.ABC):
    """
    Base class for plugins handling user objects, per school authority code.

    The plugin entry code is in the class `UserDispatcherPluginBase`.
    """

    _password_attributes = set(UserPasswords.__fields__.keys())
    _required_search_params = ("record_uid", "source_uid")
    object_type_name = "User"
    school_role_to_api_role = {
        SchoolUserRole.staff: "staff",
        SchoolUserRole.student: "student",
        SchoolUserRole.teacher: "teacher",
        SchoolUserRole.legal_guardian: "legal_guardian",
    }

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(PerSchoolAuthorityUserDispatcherBase, self).__init__(school_authority, plugin_name)
        self.class_dn_regex = school_class_dn_regex()

    async def create_or_update_preconditions_met(self, obj: ListenerUserAddModifyObject) -> bool:
        """Verify preconditions for creating or modifying object on target."""
        return await self.user_has_schools(obj)

    async def user_has_schools(self, obj: ListenerUserAddModifyObject) -> bool:
        """
        Delete user in school authority if it has no more schools in this
        school authority.
        """
        api_schools = {s.lower() for s in await self.schools_ids_on_target}
        current_schools = [s for s in obj.schools if s.lower() in api_schools]
        if not current_schools:
            await self.handle_has_no_schools(obj)
            return False
        return True

    async def print_ids(self, obj: ListenerUserAddModifyObject) -> None:
        """
        Print info about its `schools`, `record_uid` and `source_uid`.
        """
        schools_ids = await self.schools_ids_on_target
        if obj.old_data:
            old_record_uid = obj.old_data.record_uid
            old_source_uid = obj.old_data.source_uid
            old_schools = [s for s in obj.old_data.schools if s in schools_ids.keys()]
        else:
            old_record_uid = old_source_uid = old_schools = "<no old_data>"
        self.logger.debug(
            "User %r has old->new schools=(%r->%r) record_uid=(%r->%r) " "source_uid=(%r->%r).",
            obj.username,
            old_schools,
            [s for s in obj.schools if s in schools_ids],
            old_record_uid,
            obj.record_uid,
            old_source_uid,
            obj.source_uid,
        )

    async def handle_has_no_schools(self, obj: ListenerUserAddModifyObject) -> None:
        """Delete user without schools in this school authority."""
        self.logger.info(
            "All schools of user %r in this school authority (%r) have been "
            "removed. Deleting user from school authority...",
            obj.username,
            self.school_authority.name,
        )
        if obj.old_data:
            self.logger.debug(
                "User %r has 'old_data': schools=%r record_uid=%r source_uid=%r",
                obj.old_data.schools,
                obj.old_data.record_uid,
                obj.old_data.source_uid,
            )
            old_data = obj.old_data
        else:
            self.logger.debug(
                "User %r has no 'old_data', currently: schools=%r record_uid=%r source_uid=%r",
                obj.username,
                obj.schools,
                obj.record_uid,
                obj.source_uid,
            )
            old_data = ListenerUserOldDataEntry(
                record_uid=obj.record_uid,
                source_uid=obj.source_uid,
                schools=obj.schools,
            )
        remove_obj = ListenerUserRemoveObject(
            dn=obj.dn,
            id=obj.id,
            udm_object_type=obj.udm_object_type,
            action=ListenerActionEnum.delete,
            old_data=old_data,
        )
        await self.handle_remove(remove_obj)

    async def search_params(
        self, obj: Union[ListenerUserAddModifyObject, ListenerUserRemoveObject]
    ) -> Dict[str, Any]:
        """
        Usually the user is searched for using the `entryUUID` or the
        `record_uid` plus the `source_uid`.

        While the `entryUUID` is always in `obj.id`, `ListenerUserAddModifyObject`
        and `ListenerUserRemoveObject` have `record_uid` and `source_uid` in
        different parts:
        * `ListenerUserAddModifyObject`:
           - new + existing object: `obj.object["record_uid"]`, `obj.object["source_uid"]`
           - existing object: `obj.old_data.record_uid`, `obj.old_data.source_uid`
        * `ListenerUserRemoveObject`: `obj.old_data.record_uid`, `obj.old_data.source_uid`

        :param obj: user listener object
        :type obj: ListenerUserAddModifyObject or ListenerUserRemoveObject
        :return: possible parameters to use in search, currently `entryUUID´,
            `record_uid` and `source_uid`
        :rtype: dict
        """
        params = await super(PerSchoolAuthorityUserDispatcherBase, self).search_params(obj)
        if isinstance(obj, ListenerUserAddModifyObject):
            # add or modify
            params["record_uid"] = obj.record_uid
            params["source_uid"] = obj.source_uid
        if obj.old_data:
            # modify or delete
            if obj.old_data.record_uid:
                params["record_uid"] = obj.old_data.record_uid
            if obj.old_data.source_uid:
                params["source_uid"] = obj.old_data.source_uid
        # if unset, source_uid can be taken from import configuration (although record_uid will most
        # likely be missing)
        params["source_uid"] = params["source_uid"] or get_source_uid()
        return params

    async def map_attributes(
        self, obj: ListenerUserAddModifyObject, mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create dict representing the user."""
        res = await super(PerSchoolAuthorityUserDispatcherBase, self).map_attributes(obj, mapping)
        recursive_dict_update(res, self._handle_password_hashes(obj))
        return res

    @staticmethod
    async def _handle_attr_birthday(obj: ListenerUserAddModifyObject) -> Optional[datetime.date]:
        """Convert ISO 8601 'birthday' to datetime.date object."""
        if obj.object.get("birthday"):
            return datetime.datetime.strptime(obj.object["birthday"], "%Y-%m-%d").date()
        else:
            return None

    @staticmethod
    async def _handle_attr_disabled(obj: ListenerUserAddModifyObject) -> bool:
        """Pass on state of 'disabled'."""
        # second operand is for backwards compatibility (ListenerUDMVersion=1)
        return obj.object["disabled"] is True or obj.object["disabled"] == "1"

    async def _handle_attr_password(self, obj: ListenerUserAddModifyObject) -> str:
        """Generate a random password, unless password hashes are to be sent."""
        # Test for password hash handling in subclasses.
        # If they are used don't generate and set a password.
        pw = list(string.ascii_letters + string.digits + ".-_")
        random.shuffle(pw)
        return "".join(pw[:15])

    async def _handle_attr_roles(self, obj: ListenerUserAddModifyObject) -> List[str]:
        """
        `roles` attribute of UCS@school users is determined by their
        objectClasses / UDM options. Return URLs of ucsschool role in servers
        API.
        """
        try:
            api_roles = (self.school_role_to_api_role[role] for role in obj.school_user_roles)
        except KeyError:
            raise UnknownSchoolUserRole(
                f"Role unknown in internal mapping: {obj.school_user_roles!r}.",
                roles=[role.name for role in obj.school_user_roles],
            )
        return [(await self.roles_on_target)[role] for role in api_roles]

    async def _handle_attr_school(self, obj: ListenerUserAddModifyObject) -> str:
        """
        Get URL of primary school for this user.
        """
        target_schools = {k.lower(): v for k, v in (await self.schools_ids_on_target).items()}
        schools = sorted(set([obj.school] + obj.schools))
        # 1st test if primary school exists on target, so source and target can have same primary school
        # if not found try in alphanum order, same as the ucsschool.lib does, when removing users pri. OU
        schools.remove(obj.school)
        schools.insert(0, obj.school)
        for school in schools:
            try:
                return target_schools[school.lower()]
            except KeyError:
                self.logger.warning("Ignoring unknown OU %r in 'school[s]' of %r.", school, obj)
        else:
            raise UnknownSchool(
                f"None of the users schools ({schools!r}) are known on the target server.",
                school=obj.school,
            )

    async def _handle_attr_schools(self, obj: ListenerUserAddModifyObject) -> List[str]:
        """
        Get URLs of all schools in our school authority that the user is
        currently a member of.
        """
        res = []
        api_schools_cache = {k.lower(): v for k, v in (await self.schools_ids_on_target).items()}
        schools = sorted(set([obj.school] + obj.schools))
        for school in schools:
            try:
                res.append(api_schools_cache[school.lower()])
            except KeyError:
                self.logger.warning("Ignoring unknown OU %r in 'school[s]' of %r.", school, obj)
        if res:
            return res
        else:
            raise UnknownSchool(
                f"None of the users schools ({schools!r}) are known on the target server.",
                school=obj.school,
            )

    async def _handle_attr_school_classes(
        self, obj: ListenerUserAddModifyObject
    ) -> Dict[str, List[str]]:
        """Get school classes the user is in this school authority."""
        known_schools = {ou.lower() for ou in (await self.schools_ids_on_target).keys()}
        groups_dns = obj.object.get("groups", [])
        res = defaultdict(list)
        for group_dn in groups_dns:
            group_match = self.class_dn_regex.match(group_dn)
            if group_match:
                if group_match["ou"].lower() in known_schools:
                    res[group_match["ou"]].append(group_match["name"])
                else:
                    self.logger.warning(
                        "Ignoring unknown OU %r in 'school_classes' of %r (%r).",
                        group_match["ou"],
                        obj,
                        group_dn,
                    )
        res = dict(res.items())
        return res

    @staticmethod
    async def _handle_attr_source_uid(obj: ListenerUserAddModifyObject) -> str:
        """Get a source_uid."""
        return obj.source_uid or get_source_uid()

    @staticmethod
    async def _handle_attr_userexpiry(obj: ListenerUserAddModifyObject) -> Optional[datetime.date]:
        """
        Convert ISO 8601 'userexpiry' (in Kelvin called 'expiration_date') to datetime.date object.
        """
        if obj.object.get("userexpiry"):
            return datetime.datetime.strptime(obj.object["userexpiry"], "%Y-%m-%d").date()
        else:
            return None

    def _handle_password_hashes(self, obj: ListenerUserAddModifyObject) -> Dict[str, Any]:
        """
        If password hashed should be sent, return them here.

        :return: dict to update the mapping data
        """
        return {}


class UserDispatcherPluginBase(DispatcherPluginBase, abc.ABC):
    """
    Base class for plugins handling user objects.

    Send current state of user to target system (school authority).

    Each out queue has its own `UserHandlerPerSchoolAuthorityBase` instance
    which handles user data for its queues school authority.
    """

    per_s_a_handler_class: Type[PerSchoolAuthorityUserDispatcherBase] = None  # set this to your class

    @hook_impl
    async def handle_listener_object(
        self, school_authority: SchoolAuthorityConfiguration, obj: ListenerObject
    ) -> bool:
        """impl for ucsschool_id_connector.plugins.Postprocessing.handle_listener_object"""
        if isinstance(obj, ListenerUserAddModifyObject):
            await self.handler(school_authority, self.plugin_name).handle_create_or_update(obj)
        elif isinstance(obj, ListenerUserRemoveObject):
            await self.handler(school_authority, self.plugin_name).handle_remove(obj)
        else:
            return False
        return True
