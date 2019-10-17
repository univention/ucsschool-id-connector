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
from typing import Any, Callable, Dict, List, Tuple, Union

import aiofiles
import aiohttp

from .constants import (
    API_SCHOOL_CACHE_TTL,
    BB_API_MAIN_ATTRIBUTES,
    CHECK_SSL_CERTS,
    HTTP_CLIENT_TIMEOUT,
    LOG_FILE_PATH_QUEUES,
)
from .models import (
    ListenerAddModifyObject,
    ListenerRemoveObject,
    SchoolAuthorityConfiguration,
    UserPasswords,
)
from .utils import ConsoleAndFileLogging, get_source_uid

ParamType = Union[Dict[str, str], List[Tuple[str, str]]]


class APICommunicationError(Exception):
    pass


class APIRequestError(APICommunicationError):
    def __init__(self, *args, status: int, **kwargs):
        self.status = status
        super().__init__(*args, **kwargs)


class ConfigurationError(Exception):
    pass


class ServerError(APICommunicationError):
    def __init__(self, *args, status: int, **kwargs):
        self.status = status
        super().__init__(*args, **kwargs)


class UnknownRole(Exception):
    def __init__(self, *args, role: str, **kwargs):
        self.role = role
        super().__init__(*args, **kwargs)


class UnknownSchool(Exception):
    def __init__(self, *args, school: str, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)


class UserHandler:
    """
    Send current state of user to target system (school authority).

    Each out queue has its own :py:class:`UserHandler` instance which handles
    user data for the queues school authority.
    """

    _password_attributes = set(UserPasswords.__fields__.keys())

    def __init__(self, school_authority: SchoolAuthorityConfiguration):
        self.school_authority = school_authority
        self.logger = ConsoleAndFileLogging.get_logger(
            f"{self.__class__.__name__}({self.school_authority.name})",
            LOG_FILE_PATH_QUEUES,
        )
        self.api_roles_cache: Dict[str, str] = {}
        self.api_schools_cache: Dict[str, str] = {}
        self._api_schools_cache_creation = datetime.datetime(1970, 1, 1)
        timeout = aiohttp.ClientTimeout(total=HTTP_CLIENT_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def shutdown(self):
        """Clean shutdown procedure."""
        await self._session.close()

    async def handle_create_or_update(self, obj: ListenerAddModifyObject) -> None:
        """Create or modify user."""
        if not True:  # TODO
            self.logger.info(
                "All TODO entries of user %r for school authority %r have been "
                "removed or are in the past, deleting user from school authority.",
                obj.username,
                self.school_authority.name,
            )
            await self._do_remove(obj.uuid)
            return

        if True:  # TODO
            # user has currently active entries for this school authority,
            # construct data from them
            self.logger.info(
                "User %r has currently active entries for school authority %r.",
                obj.username,
                self.school_authority.name,
            )

        ucsschool_role = await self.map_role(obj)
        await self.check_role(ucsschool_role)
        await self.check_schools([])  # TODO: don't stop if at least 1 school is known
        request_body = await self.map_attributes(obj)
        await self._do_create_or_update(request_body)

    async def handle_remove(self, obj: ListenerRemoveObject) -> None:
        """Remove user."""
        await self._do_remove(obj.uuid)

    async def check_schools(self, schools: List[str]) -> None:
        """Verify that all schools are known by the target system."""
        # update list of school URLs
        if not self.api_schools_cache or (
            self._api_schools_cache_creation
            + datetime.timedelta(seconds=API_SCHOOL_CACHE_TTL)
            < datetime.datetime.now()
        ):
            self.api_schools_cache.clear()
            await self.fetch_schools()
            self._api_schools_cache_creation = datetime.datetime.now()
            self.logger.debug(
                "Updated schools known by API server: %s",
                ", ".join(self.api_schools_cache.keys()),
            )
        # verify that all schools are known
        for school in schools:
            if school not in self.api_schools_cache:
                raise UnknownSchool(
                    f"School unknown on API server: {school!r}.", school=school
                )

    async def check_role(self, role: str) -> None:
        """Verify that `role` is known by the target system."""
        if not self.api_roles_cache:
            await self.fetch_roles()
            self.logger.debug(
                "Roles known by API server: %s", ", ".join(self.api_roles_cache.keys())
            )
        if role not in self.api_roles_cache:
            raise UnknownRole(f"Role unknown on API server: {role!r}.", role=role)

    @staticmethod
    async def _get_error_msg(
        response: aiohttp.ClientResponse
    ) -> Union[Dict[str, Any], str]:
        try:
            return await response.json()
        except (ValueError, aiohttp.ContentTypeError):
            return await response.text()

    async def fetch_roles(self) -> None:
        """Fetch all roles from API of school authority."""
        url = f"{self.school_authority.url}/roles/"
        status, json_resp = await self.http_get(url)
        for role in json_resp["results"]:
            self.api_roles_cache[role["name"]] = role["url"]

    async def fetch_schools(self, name: str = None) -> None:
        """Fetch one (set `name`) or all schools from API of school authority."""
        if name:
            url = f"{self.school_authority.url}/schools/{name}/"
        else:
            url = f"{self.school_authority.url}/schools/"
        status, json_resp = await self.http_get(url)
        if name:
            self.api_schools_cache[json_resp["name"]] = json_resp["url"]
        else:
            for school in json_resp["results"]:
                self.api_schools_cache[school["name"]] = school["url"]

    async def _do_request(
        self,
        http_method: str,
        url,
        params: ParamType = None,
        acceptable_statuses: List[int] = None,
        data=None,
    ) -> Tuple[int, Dict[str, Any]]:
        acceptable_statuses = acceptable_statuses or [200]
        http_method = http_method.lower()
        headers = {
            f"Authorization": f"Token {self.school_authority.password.get_secret_value()}"
        }
        meth = getattr(self._session, http_method)
        request_kwargs = {"url": url, "headers": headers, "ssl": CHECK_SSL_CERTS}
        if http_method in {"patch", "post"} and data is not None:
            request_kwargs["json"] = data
        if params:
            request_kwargs["params"] = params
        try:
            async with meth(**request_kwargs) as response:
                if response.status in acceptable_statuses:
                    return (
                        response.status,
                        None if response.status == 204 else await response.json(),
                    )
                else:
                    self.logger.error(
                        "%s %r returned with status %r.",
                        http_method.upper(),
                        url,
                        response.status,
                    )
                    response_body = await self._get_error_msg(response)
                    self.logger.error("Response body: %r", response_body)
                    if len(response_body) > 500:
                        error_file = "/tmp/error.txt"
                        async with aiofiles.open(error_file, "w") as fp:
                            await fp.write(response_body)
                        self.logger.error("Wrote response body to %r", error_file)
                    msg = f"{http_method.upper()} {url} returned {response.status}."
                    if response.status >= 500:
                        raise ServerError(msg, status=response.status)
                    else:
                        raise APIRequestError(msg, status=response.status)
        except aiohttp.ClientConnectionError as exc:
            raise APICommunicationError(str(exc))

    async def http_delete(
        self, url, acceptable_statuses: List[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        acceptable_statuses = acceptable_statuses or [204]
        return await self._do_request(
            http_method="delete", url=url, acceptable_statuses=acceptable_statuses
        )

    async def http_get(
        self, url, params: ParamType = None, acceptable_statuses: List[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        return await self._do_request(
            http_method="get",
            url=url,
            acceptable_statuses=acceptable_statuses,
            params=params,
        )

    async def http_patch(
        self, url, data, acceptable_statuses: List[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        acceptable_statuses = acceptable_statuses or [200]
        return await self._do_request(
            http_method="patch",
            url=url,
            data=data,
            acceptable_statuses=acceptable_statuses,
        )

    async def http_post(
        self, url, data, acceptable_statuses: List[int] = None
    ) -> Tuple[int, Dict[str, Any]]:
        acceptable_statuses = acceptable_statuses or [201]
        return await self._do_request(
            http_method="post",
            url=url,
            data=data,
            acceptable_statuses=acceptable_statuses,
        )

    async def _do_create_or_update(self, data: Dict[str, Any]) -> None:
        # check if user exists, search using the UUID
        params = [
            ("record_uid", str(data["record_uid"])),
            ("source_uid", await get_source_uid()),
        ]
        url = f"{self.school_authority.url}/users/"
        status, json_resp = await self.http_get(url, params)
        if json_resp:
            # user exists, modify it
            user_url = json_resp[0]["url"]
            self.logger.info("User exists at %r.", user_url)
            status, json_resp = await self.http_patch(user_url, data=data)
            self.logger.info("User modified (status: %r): %r", status, json_resp)
        else:
            # create user
            self.logger.info("User not found, creating new one.")
            status, json_resp = await self.http_post(
                f"{self.school_authority.url}/users/", data=data
            )
            self.logger.info("User created (status: %r): %r", status, json_resp)

    async def _do_remove(self, uuid: str) -> None:
        params = [("record_uid", uuid), ("source_uid", await get_source_uid())]
        url = f"{self.school_authority.url}/users/"
        status, json_resp = await self.http_get(url, params)
        if json_resp:
            # user exists, delete it
            user_url = json_resp[0]["url"]
            self.logger.info("User exists at %r.", user_url)
            status, json_resp = await self.http_delete(user_url)
            if status == 204:
                self.logger.info("User deleted (status: %r): %r", status, json_resp)
            else:
                self.logger.error("Deleting user (status: %r): %r", status, json_resp)
        else:
            # nothing to do
            self.logger.info("User not found, finished.")

    @staticmethod
    async def map_role(obj: ListenerAddModifyObject) -> str:
        """Get role (student / teacher) of user."""
        return obj.role

    async def map_attributes(self, obj: ListenerAddModifyObject) -> Dict[str, Any]:
        """Create dict representing the user."""
        res = {}
        # set attributes configured in mapping
        for key_here, key_there in self.school_authority.mapping.items():
            if (
                key_here == "password"
                and self.school_authority.passwords_target_attribute
            ):
                self.logger.warning(
                    "'passwords_target_attribute' is set, please remove 'password' "
                    "from 'mapping'. Not sending value for 'password'."
                )
                continue

            _handle_attr_method_name = f"_handle_attr_{key_here}"
            if hasattr(self, _handle_attr_method_name):
                # handling of special attributes: try using a _handle_attr_* method
                meth: Callable[[ListenerAddModifyObject], Any] = getattr(
                    self, _handle_attr_method_name
                )
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

        # set password hashes
        if self.school_authority.passwords_target_attribute:
            pw_hashes = obj.user_passwords.dict()
            # hashes are already base64 encoded by inqueue->prepare->save
            # but have been made bytes by the pydantic Model definition
            pw_hashes["krb5Key"] = [k.decode("ascii") for k in pw_hashes["krb5Key"]]
            res.setdefault("udm_properties", {})[
                self.school_authority.passwords_target_attribute
            ] = pw_hashes

        return res

    @staticmethod
    async def _handle_attr_password(obj: ListenerAddModifyObject) -> str:
        """Generate a random password."""
        pw = list(string.ascii_letters + string.digits + ".-_")
        random.shuffle(pw)
        return "".join(pw[:15])

    async def _handle_attr_school(self, obj: ListenerAddModifyObject) -> str:
        """
        Get URL of primary school for this school authority.
        If it is in our school authority, use the 'main school' (Stammdienststelle).
        """
        main_school = []
        if main_school:
            return self.api_schools_cache[main_school[0].school]
        else:
            # no main school, use first alphabetical
            school_names = []
            return self.api_schools_cache[sorted(school_names)[0]]

    async def _handle_attr_schools(self, obj: ListenerAddModifyObject) -> List[str]:
        """
        Get URLs of all schools in our school authority that the user is
        currently a member of.
        """
        school_names = []
        return [self.api_schools_cache[school] for school in school_names]

    async def _handle_attr_school_classes(
        self, obj: ListenerAddModifyObject
    ) -> Dict[str, List[str]]:
        """Get school classes the user is in this school authority."""
        school_classes = {}
        return school_classes

    @staticmethod
    async def _handle_attr_source_uid(obj: ListenerAddModifyObject) -> str:
        """Get a source_uid."""
        return await get_source_uid()
