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

from typing import Any, Dict, List, Union

from ucsschool.kelvin.client import SchoolClass, SchoolClassResource, SchoolResource
from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.utils import school_class_dn_regex
from ucsschool_id_connector_defaults.group_handler_base import (
    GroupDispatcherPluginBase,
    GroupNotFoundError,
    PerSchoolAuthorityGroupDispatcherBase,
)
from ucsschool_id_connector_defaults.kelvin_connection import kelvin_client_session
from ucsschool_id_connector_defaults.output_plugin_handler_base import (
    SkipAttribute,
    UniquenessError,
    UnknownSchool,
)


class KelvinPerSASchoolClassDispatcher(PerSchoolAuthorityGroupDispatcherBase):
    """
    Kelvin plugin handling user objects, per school authority code.
    """

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(KelvinPerSASchoolClassDispatcher, self).__init__(school_authority, plugin_name)
        self.attribute_mapping = self.school_authority.plugin_configs[plugin_name]["mapping"][
            "school_classes"
        ]
        self._session = kelvin_client_session(school_authority, plugin_name)
        self.class_dn_regex = school_class_dn_regex()

    @property
    def session(self):
        self._session.open()
        return self._session

    async def create_or_update_preconditions_met(self, obj: ListenerGroupAddModifyObject) -> bool:
        """Verify preconditions for creating or modifying object on target."""
        if not await self.is_schools_class(obj):
            return False
        if not await self.school_class_school_exists_on_target(obj):
            self.logger.info(
                "Not creating/modifying school class %r, its school doesn't exist on the target.",
                obj.name,
            )
            return False
        return True

    async def remove_preconditions_met(self, obj: ListenerGroupRemoveObject) -> bool:
        """
        Verify preconditions for removing object on target.
        """
        if not await self.is_schools_class(obj):
            return False
        if not await self.school_class_school_exists_on_target(obj):
            self.logger.info(
                "Not creating/modifying school class %r, its school doesn't exist on the target.",
                obj.dn,
            )
            return False
        return True

    async def is_schools_class(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ) -> bool:
        """Check if group is a school class."""
        return bool(self.class_dn_regex.match(obj.dn))

    async def school_class_school_exists_on_target(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ):
        m = self.class_dn_regex.match(obj.dn)
        ou = m.groupdict()["ou"]
        return ou in await self.schools_ids_on_target

    async def fetch_schools(self) -> Dict[str, str]:
        """Fetch all schools from API of school authority."""
        return dict(
            [
                (school.name, school.name)
                async for school in SchoolResource(session=self.session).search()
            ]
        )

    async def search_params(
        self, obj: Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject]
    ) -> Dict[str, Any]:
        m = self.class_dn_regex.match(obj.dn)
        name = m.groupdict()["name"]
        school = m.groupdict()["ou"]
        return {"name": name, "school": school}

    async def fetch_obj(self, search_params: Dict[str, Any]) -> SchoolClass:
        """Retrieve a user from API of school authority."""
        users: List[SchoolClass] = [
            user async for user in SchoolClassResource(session=self.session).search(**search_params)
        ]
        if len(users) == 1:
            return users[0]
        if len(users) > 1:
            raise UniquenessError(
                f"Multiple users with the same 'source_uid'={search_params['source_uid']!r} and "
                f"'record_uid'={search_params['record_uid']!r} exist in the target system: {users!r}."
            )
        else:
            raise GroupNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a school class object at the target."""
        self.logger.info("Going to create school class: %r...", request_body)
        school_class = SchoolClass(
            session=self.session,
            **request_body,
        )
        await school_class.save()
        self.logger.info("School class created: %r.", school_class)

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: SchoolClass) -> None:
        """Modify a school class object at the target."""
        self.logger.info("Going to modify school class: %r...", api_user_data.name)
        school_class: SchoolClass = await SchoolClassResource(session=self.session).get(
            name=api_user_data.name,
            school=api_user_data.school,
        )
        for k, v in request_body.items():
            setattr(school_class, k, v)
        self.logger.debug("New state to save: %r", school_class.as_dict())
        await school_class.save()
        self.logger.info("School class modified: %r.", school_class)

    async def do_remove(self, obj: ListenerGroupRemoveObject, api_user_data: SchoolClass) -> None:
        """Delete a school class object at the target."""
        self.logger.info("Going to delete user: %r...", obj)
        school_class: SchoolClass = await SchoolClassResource(session=self.session).get(
            name=api_user_data.name,
            school=api_user_data.school,
        )
        await school_class.delete()
        self.logger.info("School class deleted: %r.", school_class)

    async def _handle_attr_name(self, obj: ListenerGroupAddModifyObject) -> str:
        """Name of this school class on the target."""
        params = await self.search_params(obj)
        return params["name"]

    async def _handle_attr_school(self, obj: ListenerGroupAddModifyObject) -> str:
        """Name of school for this school class on the target."""
        target_schools = await self.schools_ids_on_target
        params = await self.search_params(obj)
        group_ou = params["school"]
        try:
            return target_schools[group_ou]
        except KeyError:
            raise UnknownSchool(
                f"The groups school ({group_ou!r}) is not known on the target server.",
                school=group_ou,
            )

    async def _handle_attr_users(self, obj: ListenerGroupAddModifyObject) -> List[str]:
        """Usernames of members of this school class."""
        return [dn.split(",", 1)[0].split("=", 1)[1] for dn in obj.users]

    def _handle_none_value(self, key_here: str) -> Any:
        """`none` can be invalid, for example if a list is expected."""
        raise SkipAttribute()

    async def shutdown(self) -> None:
        await self._session.close()


class KelvinSchoolClassDispatcher(GroupDispatcherPluginBase):
    """
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSASchoolClassDispatcher` instance
    which handles user data for the queues school authority.
    """

    plugin_name = "kelvin"
    per_s_a_handler_class = KelvinPerSASchoolClassDispatcher
