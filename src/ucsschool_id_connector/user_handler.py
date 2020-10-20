# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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

import datetime
import random
import string
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles
import aiohttp
import ujson
from async_property import async_property

from ucsschool_id_connector.constants import (
    API_SCHOOL_CACHE_TTL,
    APPCENTER_LISTENER_PATH,
    HTTP_CLIENT_TIMEOUT,
)
from ucsschool_id_connector.ldap_access import LDAPAccess
from ucsschool_id_connector.models import (
    ListenerActionEnum,
    ListenerAddModifyObject,
    ListenerUserAddModifyObject,
    ListenerUserOldDataEntry,
    ListenerUserRemoveObject,
    SchoolAuthorityConfiguration,
    SchoolUserRole,
    UnknownSchoolUserRole,
    User,
    UserPasswords,
)
from ucsschool_id_connector.requests import http_delete, http_get, http_patch, http_post
from ucsschool_id_connector.utils import ConsoleAndFileLogging, get_source_uid, school_class_dn_regex

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


class ConfigurationError(Exception):
    pass


class MissingData(Exception):
    pass


class UnknownSchool(Exception):
    def __init__(self, *args, school: str, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)


class UserHandler:
    """
    THIS CLASS IS DEPRECATED AND WILL BE REMOVED IN FUTURE VERSIONS OF THE
    CONNECTOR THAT TARGETS KELVIN AS THE DEFAULT API.
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`UserHandler` instance which handles
    user data for the queues school authority.
    """

    _password_attributes = set(UserPasswords.__fields__.keys())
    school_role_to_bb_api_role = {
        SchoolUserRole.staff: "staff",
        SchoolUserRole.student: "student",
        SchoolUserRole.teacher: "teacher",
    }

    def __init__(self, school_authority: SchoolAuthorityConfiguration):
        self.school_authority = school_authority
        self.logger = ConsoleAndFileLogging.get_logger(
            f"{self.__class__.__name__}({self.school_authority.name})"
        )
        self.api_roles_cache: Dict[str, str] = {}
        self._api_schools_cache: Dict[str, str] = {}
        self._api_schools_cache_creation = datetime.datetime(1970, 1, 1)
        timeout = aiohttp.ClientTimeout(total=HTTP_CLIENT_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.class_dn_regex = school_class_dn_regex()

    async def shutdown(self):
        """Clean shutdown procedure."""
        await self._session.close()

    async def handle_create_or_update(self, obj: ListenerUserAddModifyObject) -> None:
        """Create or modify user."""
        # TODO: this method should be for ListenerAddModifyObject and call
        # plugins for handling specific types

        self.logger.debug("*** obj.dict()=%r", obj.dict())  # TODO: remove when stable

        # TODO: create HTTP resource to make server reload the OUs
        # for now be very inefficient and force a fetch_schools() for every user!:
        self._api_schools_cache.clear()

        current_schools = [s for s in obj.schools if s in await self.api_schools_cache]

        if not current_schools:
            await self.handle_has_no_schools(obj)
            return

        known_schools = (await self.api_schools_cache).keys()
        if obj.old_data:
            old_schools = [s for s in obj.old_data.schools if s in known_schools]
        else:
            old_schools = "<no old_data>"
        self.logger.debug(
            "User %r has old->new schools=(%r->%r) record_uid=(%r->%r) " "source_uid=(%r->%r).",
            obj.username,
            old_schools,
            current_schools,
            obj.old_data.record_uid if obj.old_data else "<no old_data>",
            obj.record_uid,
            obj.old_data.source_uid if obj.old_data else "<no old_data>",
            obj.source_uid,
        )
        request_body = await self.map_attributes(obj)
        self.logger.debug("*** request_body=%r", request_body)  # TODO: remove when stable
        await self._do_create_or_update(request_body)

    async def handle_has_no_schools(self, obj: ListenerUserAddModifyObject) -> None:
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
            self.logger.debug("User %r has no 'old_data'.")
        self.logger.debug(
            "User %r has currently: schools=%r record_uid=%r source_uid=%r",
            obj.username,
            obj.schools,
            obj.record_uid,
            obj.source_uid,
        )
        old_data = ListenerUserOldDataEntry(
            record_uid=obj.record_uid, source_uid=obj.source_uid, schools=obj.schools
        )
        remove_obj = ListenerUserRemoveObject(
            dn=obj.dn,
            id=obj.id,
            udm_object_type=obj.udm_object_type,
            action=ListenerActionEnum.delete,
            old_data=old_data,
        )
        await self._do_remove(remove_obj)

    async def handle_remove(self, obj: ListenerUserRemoveObject) -> None:
        """Remove user."""
        # TODO: this method should be force ListenerAddModifyObject and call
        # plugins for handling specific types

        # TODO: create HTTP resource to make server reload the OUs
        # for now be very inefficient and for a fetch_schools() for every user!:
        self._api_schools_cache.clear()

        await self._do_remove(obj)

    @async_property
    async def api_schools_cache(self) -> Dict[str, str]:
        """Verify that all schools are known by the target system."""
        # update list of school URLs
        if not self._api_schools_cache or (
            self._api_schools_cache_creation + datetime.timedelta(seconds=API_SCHOOL_CACHE_TTL)
            < datetime.datetime.now()
        ):
            self._api_schools_cache.clear()
            self._api_schools_cache.update(await self.fetch_schools())
            self._api_schools_cache_creation = datetime.datetime.now()
            self.logger.debug(
                "Updated schools known by API server: %s",
                ", ".join(self._api_schools_cache.keys()),
            )
        return self._api_schools_cache

    async def school_roles_to_target_roles(self, roles: List[str]) -> List[str]:
        """Convert UCS@school role IDs to target API IDs."""
        # TODO: this should be in a plugin
        if not self.api_roles_cache:
            await self.fetch_roles()
            self.logger.debug("Roles known by API server: %s", ", ".join(self.api_roles_cache.keys()))
        try:
            return [self.api_roles_cache[role] for role in roles]
        except KeyError:
            raise UnknownSchoolUserRole(f"Role(s) unknown on API server: {roles!r}.", roles=roles)

    async def fetch_roles(self) -> None:
        """Fetch all roles from API of school authority."""
        # TODO: this should be in a plugin
        url = f"{self.school_authority.url}/roles/"
        status, json_resp = await http_get(url, self.school_authority, session=self._session)
        for role in json_resp["results"]:
            self.api_roles_cache[role["name"]] = role["url"]

    async def fetch_schools(self) -> Dict[str, str]:
        """Fetch all schools from API of school authority."""
        # TODO: this should be in a plugin
        url = f"{self.school_authority.url}/schools/"
        status, json_resp = await http_get(url, self.school_authority, session=self._session)
        return dict((school["name"], school["url"]) for school in json_resp["results"])

    async def _do_create_or_update(self, data: Dict[str, Any]) -> None:
        # TODO: this should be in a plugin
        # check if user exists, search using the IDs
        params = {
            "record_uid": str(data.get("record_uid")),
            "source_uid": data.get("source_uid") or await get_source_uid(),
        }
        if not all(list(params.values())):
            raise MissingData(
                f"Cannot add/modify user: missing record_uid or source_uid in data: {data!r}."
            )
        url = f"{self.school_authority.url}/users/"
        status, json_resp = await http_get(url, self.school_authority, params, session=self._session)
        if json_resp:
            # user exists, modify it
            user_url = json_resp[0]["url"]
            self.logger.info("User exists at %r.", user_url)
            status, json_resp = await http_patch(
                user_url, self.school_authority, session=self._session, data=data
            )
            self.logger.info("User modified (status: %r): %r", status, json_resp)
        else:
            # create user
            self.logger.info("User not found, creating new one.")
            status, json_resp = await http_post(
                f"{self.school_authority.url}/users/",
                self.school_authority,
                session=self._session,
                data=data,
            )
            self.logger.info("User created (status: %r): %r", status, json_resp)

    async def _do_remove(self, obj: ListenerUserRemoveObject) -> None:
        params = {
            "record_uid": obj.old_data.record_uid,
            "source_uid": obj.old_data.source_uid or await get_source_uid(),
        }
        if not all(list(params.values())):
            raise MissingData(f"Cannot remove user: missing record_uid or source_uid in {obj!r}.")
        url = f"{self.school_authority.url}/users/"
        status, json_resp = await http_get(url, self.school_authority, params, session=self._session)
        if json_resp:
            # user exists, delete it
            user_url = json_resp[0]["url"]
            self.logger.info("User exists at %r.", user_url)
            status, json_resp = await http_delete(user_url, self.school_authority, session=self._session)
            if status == 204:
                self.logger.info("User deleted (status: %r): %r", status, json_resp)
            else:
                self.logger.error("Deleting user (status: %r): %r", status, json_resp)
        else:
            # nothing to do
            self.logger.info("User not found, finished.")

    async def map_attributes(self, obj: ListenerAddModifyObject) -> Dict[str, Any]:
        """Create dict representing the user."""
        # TODO: this should be in a plugin
        res = {}
        # set attributes configured in mapping
        for key_here, key_there in self.school_authority.mapping.items():
            if key_here == "password" and self.school_authority.passwords_target_attribute:
                self.logger.warning(
                    "'passwords_target_attribute' is set, please remove 'password' "
                    "from 'mapping'. Not sending value for 'password'."
                )
                continue

            _handle_attr_method_name = f"_handle_attr_{key_here}"
            if hasattr(self, _handle_attr_method_name):
                # handling of special attributes: try using a _handle_attr_* method
                meth: Callable[[ListenerAddModifyObject], Any] = getattr(self, _handle_attr_method_name)
                value_here = await meth(obj)
            else:
                # no such method, use value from listener file directly
                value_here = obj.object.get(key_here)

            # `none` is mostly invalid for the school authorities API
            if value_here is None:
                continue

            # TODO: make BB-API a pluggable API strategy (currently the only one)
            if key_there in BB_API_MAIN_ATTRIBUTES:
                res[key_there] = value_here
            else:
                res.setdefault("udm_properties", {})[key_there] = value_here

        if isinstance(obj, ListenerUserAddModifyObject):
            # set password hashes
            if self.school_authority.passwords_target_attribute and obj.user_passwords:
                pw_hashes = obj.user_passwords.dict()
                # hashes are already base64 encoded by inqueue->prepare->save
                # but have been made bytes by the pydantic Model definition
                pw_hashes["krb5Key"] = [k.decode("ascii") for k in pw_hashes["krb5Key"]]
                res.setdefault("udm_properties", {})[
                    self.school_authority.passwords_target_attribute
                ] = pw_hashes

        return res

    @staticmethod
    async def _handle_attr_disabled(obj: ListenerUserAddModifyObject) -> bool:
        """Pass on state of 'disabled'."""
        return obj.object["disabled"] == "1"

    @staticmethod
    async def _handle_attr_password(obj: ListenerUserAddModifyObject) -> str:
        """Generate a random password."""
        pw = list(string.ascii_letters + string.digits + ".-_")
        random.shuffle(pw)
        return "".join(pw[:15])

    async def _handle_attr_roles(self, obj: ListenerUserAddModifyObject) -> List[str]:
        """
        `roles` attribute of UCS@school users is determined by their
        objectClasses / UDM options. Return URLs of ucsschool role in servers
        API.
        """
        # TODO: this should be in a plugin
        try:
            bb_api_roles = (self.school_role_to_bb_api_role[role] for role in obj.school_user_roles)
        except KeyError:
            raise UnknownSchoolUserRole(
                f"Role unknown in internal mapping: {obj.school_user_roles!r}.",
                roles=[role.name for role in obj.school_user_roles],
            )
        return [self.api_roles_cache[role] for role in bb_api_roles]

    async def _handle_attr_school(self, obj: ListenerUserAddModifyObject) -> str:
        """
        Get URL of primary school for this user.
        """
        api_schools_cache = await self.api_schools_cache
        schools = sorted(set([obj.school] + obj.schools))
        for school in schools:
            try:
                return api_schools_cache[school]
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
        api_schools_cache = await self.api_schools_cache
        schools = sorted(set([obj.school] + obj.schools))
        for school in schools:
            try:
                res.append(api_schools_cache[school])
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
        known_schools = (await self.api_schools_cache).keys()
        groups_dns = obj.object.get("groups", [])
        res = defaultdict(list)
        for group_dn in groups_dns:
            group_match = self.class_dn_regex.match(group_dn)
            if group_match:
                if group_match["ou"] in known_schools:
                    res[group_match["ou"]].append(group_match["name"])
                else:
                    self.logger.warning(
                        "Ignoring unknown OU %r in 'school_classes' of %r.",
                        group_match["ou"],
                        obj,
                    )
        res = dict(res.items())
        self.logger.debug("User %r has school_classes: %r.", obj.username, res)
        return res

    @staticmethod
    async def _handle_attr_source_uid(obj: ListenerUserAddModifyObject) -> str:
        """Get a source_uid."""
        return obj.source_uid or await get_source_uid()


class UserScheduler:
    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self.ldap_access = LDAPAccess()

    async def get_user_from_ldap(self, username: str) -> Optional[User]:
        return await self.ldap_access.get_user(username, attributes=["*", "entryUUID"])

    @staticmethod
    async def write_listener_file(user: User) -> None:
        """
        Create JSON file to trigger appcenter converter service to create JSON
        file for our app container.

        We cannot create listener files (`ListenerObject`) like the appcenter
        converter service does, because we don't have UDM. So we'll create the
        files the appcenter listener creates. They will trigger the appcenter
        converter service to write the listener files (`ListenerObject`).

        This is what the appcenter listener does in
        management/univention-appcenter/python/appcenter/listener.py in
        `AppListener._write_json()`.
        """
        attrs = {
            "entry_uuid": user.attributes["entryUUID"][0],
            "dn": user.dn,
            "object_type": "users/user",
            "command": "m",
        }
        json_s = ujson.dumps(attrs, sort_keys=True, indent=4)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        path = Path(APPCENTER_LISTENER_PATH, f"{timestamp}.json")
        async with aiofiles.open(path, "w") as fp:
            await fp.write(json_s)

    async def queue_user(self, username: str) -> None:
        self.logger.debug("Searching LDAP for user with username %r...", username)
        user = await self.get_user_from_ldap(username)
        if user:
            self.logger.info("Adding user to in-queue: %r.", user.dn)
            await self.write_listener_file(user)
        else:
            self.logger.error("No school user with username %r could be found.", username)
