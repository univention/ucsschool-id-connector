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

"""
Client for the ID Broker Provisioning API.
"""
import abc
import datetime
import logging
import os
import re
from typing import Dict, List, Match, Optional, Type, Union, cast

import jwt
import lazy_object_proxy
from async_property import async_property
from pydantic import BaseModel

from ucsschool_id_connector.models import SchoolAuthorityConfiguration
from ucsschool_id_connector.utils import ConsoleAndFileLogging

from .provisioning_api import (
    ApiClient,
    ApiException,
    AuthApi,
    Configuration as GenConfiguration,
    School as GenSchool,
    SchoolClass as GenSchoolClass,
    SchoolClassesApi as GenSchoolClassesApi,
    SchoolContext as GenSchoolContext,
    SchoolsApi as GenSchoolsApi,
    Token as GenToken,
    User as GenUser,
    UsersApi as GenUsersApi,
)

logger: logging.Logger = lazy_object_proxy.Proxy(lambda: ConsoleAndFileLogging.get_logger(__name__))
_shared_token: Optional["Token"] = None

GenApiObject = Union[GenSchool, GenSchoolClass, GenSchoolContext, GenUser]
GenApiHandler = Union[GenSchoolsApi, GenSchoolClassesApi, GenUsersApi]
IDBrokerObject = Union["School", "SchoolClass", "SchoolContext", "User"]
IDBrokerObjectType = Union[Type["School"], Type["SchoolClass"], Type["SchoolContext"], Type["User"]]


def _get_shared_token() -> Optional["Token"]:
    return _shared_token


def _set_shared_token(token: "Token") -> None:
    global _shared_token
    _shared_token = token


class IDBrokerError(Exception):
    def __init__(self, status: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = status


class IDBrokerNotFoundError(IDBrokerError):
    status = 404


class IDBrokerObjectBase(BaseModel):
    _gen_class: Type[GenApiObject]

    @classmethod
    def from_gen_obj(cls, gen_obj: GenApiObject) -> BaseModel:
        """Convert OpenAPI client object to pydantic object."""
        return cls(**{k: v for k, v in gen_obj.to_dict().items()})

    def to_gen_obj(self) -> GenApiObject:
        """Convert pydantic object to OpenAPI client object."""
        return self._gen_class(**{k: v for k, v in self.dict().items()})

    def __eq__(self, other):
        return self.dict() == other.dict()


class School(IDBrokerObjectBase):
    name: str
    display_name: str
    _gen_class = GenSchool


class SchoolClass(IDBrokerObjectBase):
    name: str
    description: str
    school: str
    members: List[str]
    _gen_class = GenSchoolClass


class SchoolContext(IDBrokerObjectBase):
    classes: List[str]
    roles: List[str]
    _gen_class = GenSchoolContext


class User(IDBrokerObjectBase):
    id: str
    first_name: str
    last_name: str
    user_name: str
    context: Dict[str, SchoolContext]
    _gen_class = GenUser

    @classmethod
    def from_gen_obj(cls, gen_obj: GenApiObject) -> "User":
        gen_obj = cast(GenUser, gen_obj)
        res = super().from_gen_obj(gen_obj)
        res = cast("User", res)
        res.context = {
            k: SchoolContext(classes=v.classes, roles=v.roles) for k, v in gen_obj.context.items()
        }
        return res

    def to_gen_obj(self) -> GenUser:
        res = super().to_gen_obj()
        res = cast(GenUser, res)
        res.context = {
            k: GenSchoolContext(classes=v.classes, roles=v.roles) for k, v in self.context.items()
        }
        return res


class Token:
    def __init__(self, api_configuration: GenConfiguration):
        self._configuration = api_configuration
        self._token: Optional[GenToken] = None
        self._token_expiry: Optional[datetime.datetime] = None

    @async_property
    async def access_token(self) -> str:
        """Get the access token, refreshed if required."""
        if not self._token or not self._token_is_valid():
            self._token = await self._fetch_token()
            self._token_expiry = self._token_expiration(self._token.access_token)
            if self._token_expiry < datetime.datetime.utcnow():
                raise ValueError(
                    f"Retrieved expired token. Token expiry is: {self._token_expiry.isoformat()} UTC. "
                    f"Current time is {datetime.datetime.utcnow().isoformat()} UTC."
                )
        return self._token.access_token

    @staticmethod
    def _token_expiration(access_token: str) -> datetime.datetime:
        """Get the time at which `access_token` expires."""
        try:
            payload = jwt.decode(
                access_token,
                algorithms=["HS256"],
                options={"verify_exp": False, "verify_signature": False},
            )
        except jwt.PyJWTError as exc:
            raise ValueError(f"Error decoding token ({access_token!r}): {exc!s}")
        if not isinstance(payload, dict) or "exp" not in payload:
            raise ValueError(f"Payload in token not a dict or missing 'exp' entry ({access_token!r}).")
        try:
            return datetime.datetime.utcfromtimestamp(payload["exp"])
        except ValueError as exc:
            raise ValueError(
                f"Error parsing date {payload['exp']!r} in token ({access_token!r}): {exc!s}"
            )

    def _token_is_valid(self) -> bool:
        if not self._token_expiry or not self._token:
            return False
        if datetime.datetime.utcnow() > self._token_expiry:
            return False
        return True

    async def _fetch_token(self) -> GenToken:
        logger.debug("Retrieving token...")
        async with ApiClient(self._configuration) as api_client:
            api_instance = AuthApi(api_client)
            api_response = await api_instance.login_for_access_token_ucsschool_apis_auth_token_post(
                username=self._configuration.username,
                password=self._configuration.password,
                grant_type="password",
            )
            return api_response


class ProvisioningAPIClient(abc.ABC):
    API_METHODS: Dict[str, str]
    PROVISIONING_URL_REGEX = r"^https://(?P<host>.+?)/"
    _object_type: IDBrokerObjectType
    _gen_api_handler: Type[GenApiHandler]
    _share_token = True  # whether all client instances should use the same Token instance

    def __init__(self, school_authority: SchoolAuthorityConfiguration, plugin_name: str):
        self.school_authority = school_authority
        self.plugin_name = plugin_name
        m: Optional[Match] = re.match(self.PROVISIONING_URL_REGEX, school_authority.url)
        if not m:
            raise ValueError(
                f"Bad ID Broker Provisioning URL in school authority configuration {school_authority!r}:"
                f" {school_authority.url!r}. Correct form is: 'https://FQDN/'."
            )
        host = m.groupdict()["host"]
        target_url = f"https://{host}"
        try:
            self.school_authority_name = school_authority.name
            username = school_authority.plugin_configs[plugin_name]["username"]
            password = school_authority.plugin_configs[plugin_name]["password"].get_secret_value()
            version = school_authority.plugin_configs[plugin_name]["version"]
        except KeyError as exc:
            raise ValueError(
                f"Missing {exc!s} in ID Broker Provisioning plugin configuration of school authority: "
                f"{school_authority.dict()!r}."
            )
        if version != 1:
            raise ValueError(f"Unsupported ID Broker Provisioning API version {version!r}.")
        self.configuration = GenConfiguration(host=target_url, username=username, password=password)
        self.configuration.verify_ssl = "UNSAFE_SSL" not in os.environ
        shared_token = _get_shared_token()
        if self._share_token and shared_token:
            self.token = shared_token
        else:
            self.token = Token(self.configuration)
            if self._share_token:
                _set_shared_token(self.token)

    async def _create(self, obj_arg_name: str, **kwargs) -> IDBrokerObject:
        """
        Create object.

        `obj_arg_name` is the key to the object to create in kwargs that has to be used in the API call.
        Returned value is the object actually created by the server.
        """
        obj = cast(IDBrokerObject, kwargs.pop(obj_arg_name))
        logger.debug("Creating %s %r...", self._object_type.__name__, obj)
        gen_obj = obj.to_gen_obj()
        kwargs[obj_arg_name] = gen_obj
        try:
            new_obj = await self._request("post", **kwargs)
        except ApiException as exc:
            exc_cls = IDBrokerNotFoundError if exc.status == 404 else IDBrokerError
            raise exc_cls(
                exc.status,
                f"Error HTTP {exc.status} ({exc.reason}) creating {self._object_type.__name__} "
                f"{gen_obj!r}.",
            )
        if not new_obj:
            raise RuntimeError(
                f"Empty response creating {self._object_type.__name__} object {gen_obj!r}."
            )
        logger.debug("Created %s: %r", self._object_type.__name__, new_obj)
        if obj != new_obj:
            logger.warning(
                "Requested %s to be created and object returned by server differ."
                "Requested object:\n%r, returned object:\n%r",
                self._object_type.__name__,
                obj.dict(),
                new_obj.dict(),
            )
        return new_obj

    async def _delete(self, id_arg_name: str, **kwargs) -> None:
        """Delete object with id `obj_id`."""
        obj_id = kwargs.pop(id_arg_name)
        logger.debug("Deleting %s %r...", self._object_type.__name__, obj_id)
        kwargs[id_arg_name] = obj_id
        try:
            await self._request("delete", **kwargs)
            logger.debug("%s %r deleted.", self._object_type.__name__, obj_id)
        except ApiException as exc:
            if exc.status != 404:
                raise IDBrokerError(
                    exc.status,
                    f"Error HTTP {exc.status} ({exc.reason}) deleting {self._object_type.__name__} "
                    f"{obj_id!r}.",
                )
            logger.info("%s %r not deleted, as it did not exist.", self._object_type.__name__, obj_id)

    async def _exists(self, id_arg_name: str, **kwargs) -> bool:
        """
        Check if an object exists on the server.

        `id_arg_name` is the key to the id in kwargs that has to be used in the API call.
        """
        obj_id = kwargs.pop(id_arg_name)
        logger.debug("Checking existence of %s %r...", self._object_type.__name__, obj_id)
        kwargs[id_arg_name] = obj_id
        try:
            await self._request("head", **kwargs)
            logger.debug("%s %r exists.", self._object_type.__name__, obj_id)
        except ApiException as exc:
            if exc.status != 404:
                raise IDBrokerError(
                    exc.status,
                    f"Error HTTP {exc.status} ({exc.reason}) checking existence of "
                    f"{self._object_type.__name__} using {kwargs!r}.",
                )
            logger.debug("%s %r does not exist.", self._object_type.__name__, obj_id)
            return False
        return True

    async def _get(self, **kwargs) -> IDBrokerObject:
        """Retrieve the object from the server."""
        logger.debug("Retrieving %s using %r...", self._object_type.__name__, kwargs)
        try:
            obj = await self._request("get", **kwargs)
        except ApiException as exc:
            exc_cls = IDBrokerNotFoundError if exc.status == 404 else IDBrokerError
            raise exc_cls(
                exc.status,
                f"Error HTTP {exc.status} ({exc.reason}) retrieving {self._object_type.__name__} "
                f"using {kwargs!r}.",
            )
        if not obj:
            raise RuntimeError(
                f"Empty response retrieving {self._object_type.__name__} object with {kwargs!r}."
            )
        logger.debug("Retrieved %s: %r", self._object_type.__name__, obj)
        return obj

    async def _update(self, obj_arg_name: str, **kwargs) -> IDBrokerObject:
        """
        Modify object on the server

        `obj_arg_name` is the key to the object to modify in kwargs that has to be used in the API call.
        Returned value is the object actually created by the server.
        """
        obj = cast(IDBrokerObject, kwargs.pop(obj_arg_name))
        logger.debug("Updating %s %r...", self._object_type.__name__, obj)
        gen_obj = obj.to_gen_obj()
        kwargs[obj_arg_name] = gen_obj
        try:
            new_obj = await self._request("put", **kwargs)
        except ApiException as exc:
            exc_cls = IDBrokerNotFoundError if exc.status == 404 else IDBrokerError
            raise exc_cls(
                exc.status,
                f"Error HTTP {exc.status} ({exc.reason}) updating {self._object_type.__name__} "
                f"{gen_obj!r}.",
            )
        if not new_obj:
            raise RuntimeError(f"Empty response updating {self._object_type.__name__} {gen_obj!r}.")
        logger.debug("Updated %s: %r", self._object_type.__name__, new_obj)
        if obj != new_obj:
            logger.warning(
                "Requested %s to be updated and object returned by server differ."
                "Requested object:\n%r, returned object:\n%r",
                self._object_type.__name__,
                obj.dict(),
                new_obj.dict(),
            )
        return new_obj

    async def _request(self, method: str, *args, **kwargs) -> Optional[IDBrokerObject]:
        self.configuration.access_token = await self.token.access_token
        async with ApiClient(self.configuration) as api_client:
            api_instance = self._gen_api_handler(api_client)
            meth = getattr(api_instance, self.API_METHODS[method])
            res = await meth(*args, **kwargs)
        if res:
            gen_obj = cast(GenApiObject, res)
            obj = self._object_type.from_gen_obj(gen_obj)
            obj = cast(IDBrokerObject, obj)
            return obj  # GET, POST, PUT
        return res  # DELETE: None


class IDBrokerUser(ProvisioningAPIClient):
    API_METHODS = {
        "delete": "delete_ucsschool_apis_provisioning_v1_school_authority_users_user_id_delete",
        "get": "get_ucsschool_apis_provisioning_v1_school_authority_users_user_id_get",
        "head": "get_head_ucsschool_apis_provisioning_v1_school_authority_users_user_id_head",
        "post": "post_ucsschool_apis_provisioning_v1_school_authority_users_post",
        "put": "put_ucsschool_apis_provisioning_v1_school_authority_users_user_id_put",
    }
    _object_type = User
    _gen_api_handler = GenUsersApi

    async def create(self, user: User) -> User:
        """Create user. Returned value is the data from the server."""
        res = await super()._create(
            obj_arg_name="user", school_authority=self.school_authority_name, user=user
        )
        return cast(User, res)

    async def delete(self, user_id: str) -> None:
        """Delete user with id `user_id`."""
        await self._delete(
            id_arg_name="user_id", school_authority=self.school_authority_name, user_id=user_id
        )

    async def exists(self, user_id: str) -> bool:
        """Check if the user with the ID `user_id` exists on the server."""
        return await self._exists(
            id_arg_name="user_id", school_authority=self.school_authority_name, user_id=user_id
        )

    async def get(self, user_id: str) -> User:
        res = await super()._get(school_authority=self.school_authority_name, user_id=user_id)
        return cast(User, res)

    async def update(self, user: User) -> User:
        """Modify the user with the ID `user.id` on the server."""
        res = await super()._update(
            obj_arg_name="user",
            school_authority=self.school_authority_name,
            user_id=user.id,
            user=user,
        )
        return cast(User, res)


class IDBrokerSchool(ProvisioningAPIClient):
    API_METHODS = {
        "get": "get_ucsschool_apis_provisioning_v1_school_authority_schools_name_get",
        "head": "get_head_ucsschool_apis_provisioning_v1_school_authority_schools_name_head",
        "post": "post_ucsschool_apis_provisioning_v1_school_authority_schools_post",
    }
    _object_type = School
    _gen_api_handler = GenSchoolsApi

    async def create(self, school: School) -> School:
        """Create school. Returned value is the data from the server."""
        res = await super()._create(
            obj_arg_name="school", school_authority=self.school_authority_name, school=school
        )
        return cast(School, res)

    async def exists(self, name: str) -> bool:
        """Check if the school with the name `name` exists on the server."""
        return await self._exists(
            id_arg_name="name", school_authority=self.school_authority_name, name=name
        )

    async def get(self, name: str) -> School:
        res = await super()._get(school_authority=self.school_authority_name, name=name)
        return cast(School, res)


class IDBrokerSchoolClass(ProvisioningAPIClient):
    API_METHODS = {
        "get": "get_ucsschool_apis_provisioning_v1_school_authority_classes_school_name_get",
        "head": "get_head_ucsschool_apis_provisioning_v1_school_authority_classes_school_name_head",
        "post": "post_ucsschool_apis_provisioning_v1_school_authority_classes_post",
        "put": "put_ucsschool_apis_provisioning_v1_school_authority_classes_school_name_put",
        "delete": "delete_ucsschool_apis_provisioning_v1_school_authority_classes_school_name_delete",
    }
    _object_type = SchoolClass
    _gen_api_handler = GenSchoolClassesApi

    async def create(self, school_class: SchoolClass) -> SchoolClass:
        """Create schoolclass. Returned value is the data from the server."""
        res = await super()._create(
            obj_arg_name="school_class",
            school_authority=self.school_authority_name,
            school_class=school_class,
        )
        return cast(SchoolClass, res)

    async def exists(self, name: str, school: str) -> bool:
        """Check if the schoolclass with the name `name` and the school `school` exists on the server."""
        return await self._exists(
            id_arg_name="name", school_authority=self.school_authority_name, name=name, school=school
        )

    async def get(self, name: str, school: str) -> SchoolClass:
        res = await super()._get(school_authority=self.school_authority_name, name=name, school=school)
        return cast(SchoolClass, res)

    async def update(self, school_class: SchoolClass) -> SchoolClass:
        """Modify the schoolclass with the name `school_class.name`
        and the school `school_class.school` on the server."""
        res = await super()._update(
            obj_arg_name="school_class",
            school_authority=self.school_authority_name,
            name=school_class.name,
            school=school_class.school,
            school_class=school_class,
        )
        return cast(SchoolClass, res)

    async def delete(self, name: str, school: str) -> None:
        """Delete school_class with `name` in `school`."""
        await self._delete(
            id_arg_name="name", school_authority=self.school_authority_name, name=name, school=school
        )
