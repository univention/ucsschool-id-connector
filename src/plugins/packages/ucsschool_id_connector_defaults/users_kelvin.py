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

from ucsschool.kelvin.client import PasswordsHashes, RoleResource, SchoolResource, User, UserResource
from ucsschool_id_connector.models import (
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.utils import ucsschool_role_regex
from ucsschool_id_connector_defaults.kelvin_connection import kelvin_client_session
from ucsschool_id_connector_defaults.output_plugin_handler_base import SkipAttribute, UniquenessError
from ucsschool_id_connector_defaults.user_handler_base import (
    PerSchoolAuthorityUserDispatcherBase,
    UserDispatcherPluginBase,
    UserNotFoundError,
)

KELVIN_API_SCHOOL_ATTRIBUTES = {
    "name",
    "birthday",
    "disabled",
    "email",
    "expiration_date",
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
KELVIN_API_PASSWORD_HASHES_ATTRIBUTE = "kelvin_password_hashes"  # nosec


class SSLCACertificateDownloadError(Exception):
    ...


class KelvinPerSAUserDispatcher(PerSchoolAuthorityUserDispatcherBase):
    """
    Kelvin plugin handling user objects, per school authority code.
    """

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        super(KelvinPerSAUserDispatcher, self).__init__(school_authority, plugin_name)
        self.attribute_mapping = self.school_authority.plugin_configs[plugin_name]["mapping"]
        self._session = kelvin_client_session(school_authority, plugin_name)

    @property
    def session(self):
        self._session.open()
        return self._session

    async def fetch_roles(self) -> Dict[str, str]:
        """Fetch all roles from API of school authority."""
        return dict(
            [(role.name, role.name) async for role in RoleResource(session=self.session).search()]
        )

    async def fetch_schools(self) -> Dict[str, str]:
        """Fetch all schools from API of school authority."""
        return dict(
            [
                (school.name, school.name)
                async for school in SchoolResource(session=self.session).search()
            ]
        )

    async def search_params(
        self, obj: Union[ListenerUserAddModifyObject, ListenerUserRemoveObject]
    ) -> Dict[str, Any]:
        res = await super(KelvinPerSAUserDispatcher, self).search_params(obj)
        # filter out unwanted search parameters
        return {
            "record_uid": res["record_uid"],
            "source_uid": res["source_uid"],
        }

    async def fetch_obj(self, search_params: Dict[str, Any]) -> User:
        """Retrieve a user from API of school authority."""
        self.logger.debug("Retrieving user with search parameters: %r", search_params)
        users: List[User] = [
            user async for user in UserResource(session=self.session).search(**search_params)
        ]
        if len(users) == 1:
            return users[0]
        if len(users) > 1:
            raise UniquenessError(
                f"Multiple users with the same 'source_uid'={search_params['source_uid']!r} and "
                f"'record_uid'={search_params['record_uid']!r} exist in the target system: {users!r}."
            )
        else:
            raise UserNotFoundError(f"No user found with search params: {search_params!r}.")

    async def do_create(self, request_body: Dict[str, Any]) -> None:
        """Create a user object at the target."""
        self.logger.info("Going to create user %r: %r...", request_body["name"], request_body)
        user = User(
            session=self.session,
            **request_body,
        )
        await user.save()
        self.logger.info("User created: %r.", user)

    async def do_modify(self, request_body: Dict[str, Any], api_user_data: User) -> None:
        """Modify a user object at the target."""
        self.logger.info("Going to modify user %r: %r...", api_user_data.name, request_body)
        user: User = await UserResource(session=self.session).get(name=api_user_data.name)
        for k, v in request_body.items():
            setattr(user, k, v)
        await user.save()
        self.logger.info("User modified: %r.", user)

    async def do_remove(self, obj: ListenerUserRemoveObject, api_user_data: User) -> None:
        """Delete a user object at the target."""
        self.logger.info("Going to delete user: %r...", obj)
        user: User = await UserResource(session=self.session).get(name=api_user_data.name)
        await user.delete()
        self.logger.info("User deleted: %r.", user)

    async def map_attributes(
        self, obj: ListenerUserAddModifyObject, mapping: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Create dict representing the object.

        The mapping in the kelvin plugin has to select the appropriate mapping
        depending on the users roles
        """
        roles = obj.object.get("ucsschoolRole", [])
        used_mapping = await self._get_role_specific_mapping(roles, mapping)
        return await super().map_attributes(obj, used_mapping)

    async def _get_role_specific_mapping(
        self, roles: List[str], mapping: Dict[str, Dict]
    ) -> Dict[str, str]:
        """
        Returns the correct mapping to use for map_attributes
        based on the given roles and configured mappings in the school authority
        """
        pattern = ucsschool_role_regex()
        handled_schools = [school.lower() for school in await self.handled_schools()]
        role_dicts = [match.groupdict() for match in (pattern.search(role) for role in roles) if match]
        user_roles = [
            obj["role"]
            for obj in role_dicts
            if obj["context_type"] == "school" and obj["context"].lower() in handled_schools
        ]
        if "school_admin" in user_roles and "users_school_admin" in mapping:
            key = "users_school_admin"
        elif "staff" in user_roles and "users_staff" in mapping:
            key = "users_staff"
        elif "teacher" in user_roles and "users_teacher" in mapping:
            key = "users_teacher"
        elif "student" in user_roles and "users_student" in mapping:
            key = "users_student"
        else:
            key = "users"
        self.logger.info(f"Using {key} for the user mapping")
        return mapping[key]

    async def _handle_attr_password(self, obj: ListenerUserAddModifyObject) -> str:
        """Generate a random password, unless password hashes are to be sent."""
        if self.school_authority.plugin_configs[self.plugin_name].get("sync_password_hashes", False):
            self.logger.warning(
                "Configuration key 'sync_password_hashes' is set, please remove 'password' from "
                "'mapping'. Not sending value for 'password'.",
            )
            raise SkipAttribute()
        return await super(KelvinPerSAUserDispatcher, self)._handle_attr_password(obj)

    def _handle_none_value(self, key_here: str) -> Any:
        """`none` can be invalid, for example if a list is expected."""
        if key_here in ("birthday", "userexpiry"):
            return None
        raise SkipAttribute()

    def _update_for_mapping_data(self, key_here: str, key_there: str, value_here: Any) -> Dict[str, Any]:
        """Structure the data mapping result for the target API."""
        if key_there in KELVIN_API_SCHOOL_ATTRIBUTES:
            return {key_there: value_here}
        else:
            return {"udm_properties": {key_there: value_here}}

    def _handle_password_hashes(self, obj: ListenerUserAddModifyObject) -> Dict[str, Any]:
        """If password hashed should be sent, return them here."""
        if (
            self.school_authority.plugin_configs[self.plugin_name].get("sync_password_hashes", False)
            and obj.user_passwords
        ):
            hashes = obj.user_passwords.dict_krb5_key_base64_encoded()
            return {
                KELVIN_API_PASSWORD_HASHES_ATTRIBUTE: PasswordsHashes(
                    user_password=hashes["userPassword"],
                    samba_nt_password=hashes["sambaNTPassword"],
                    krb_5_key=hashes["krb5Key"],
                    krb5_key_version_number=hashes["krb5KeyVersionNumber"],
                    samba_pwd_last_set=hashes["sambaPwdLastSet"],
                )
            }
        return {}

    async def shutdown(self) -> None:
        await self._session.close()


class KelvinUserDispatcher(UserDispatcherPluginBase):
    """
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`KelvinPerSAUserDispatcher` instance
    which handles user data for the queues school authority.
    """

    plugin_name = "kelvin"
    per_s_a_handler_class = KelvinPerSAUserDispatcher
