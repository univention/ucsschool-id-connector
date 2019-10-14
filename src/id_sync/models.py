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

import base64
import logging
from enum import Enum
from typing import Any, Dict, List, Set, Type, Union

import lazy_object_proxy
from pydantic import BaseModel, PydanticValueError, SecretStr, UrlStr, validator

from .utils import ConsoleAndFileLogging

# for debugging during coding
logger: logging.Logger = lazy_object_proxy.Proxy(
    lambda: ConsoleAndFileLogging.get_logger(__name__)
)


class ListenerFileAttributeError(PydanticValueError):
    code = "invalid_listener_file"
    msg_template = 'Missing or empty value in listener file: "{key}"="{value}"'


class MissingArgumentError(PydanticValueError):
    code = "missing_argument"
    msg_template = 'value is missing or empty "{missing_argument}"'


class NoObjectError(PydanticValueError):
    code = "no_object"
    msg_template = 'no object found with "{key}"="{value}"'


class ObjectExistsError(PydanticValueError):
    code = "object_exists"
    msg_template = 'object with "{key}"="{value}" already exists'


class UserPasswords(BaseModel):
    userPassword: List[str]
    sambaNTPassword: str
    krb5Key: List[bytes]
    krb5KeyVersionNumber: int
    sambaPwdLastSet: int

    def dict_krb5_key_base64_encoded(
        self,
        *,
        include: Set[str] = None,
        exclude: Set[str] = None,
        by_alias: bool = False,
        skip_defaults: bool = False,
    ) -> Dict[str, Any]:
        """wrapper around :py:meth:`dict()` that base64 encodes `krb5Key`"""
        res = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )
        res["krb5Key"] = [base64.b64encode(k).decode("ascii") for k in res["krb5Key"]]
        return res


class ListenerObject(BaseModel):
    dn: str
    id: str
    object: Dict[str, Any]
    options: List[str]
    udm_object_type: str

    def __hash__(self):
        return hash(self.id)

    @validator("udm_object_type")
    def supported_udm_object_type(cls, value):
        raise NotImplementedError("Implement this in an object specific subclass.")

    @property
    def uuid(self) -> str:
        return self.object["UUID"]


class UserListenerObject(ListenerObject):
    user_passwords: UserPasswords = None

    @validator("udm_object_type")
    def supported_udm_object_type(cls, value):
        if value != "users/user":
            raise ListenerFileAttributeError(key="udm_object_type", value=value)
        return value

    @property
    def role(self) -> str:
        # TODO: plugin start
        return "teacher"
        # TODO: plugin end

    @property
    def username(self) -> str:
        return self.object["username"]

    def dict_krb5_key_base64_encoded(
        self,
        *,
        include: Set[str] = None,
        exclude: Set[str] = None,
        by_alias: bool = False,
        skip_defaults: bool = False,
    ) -> Dict[str, Any]:
        """wrapper around :py:meth:`dict()` that base64 encodes `user_passwords.krb5Key`"""
        res = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )
        res["user_passwords"] = self.user_passwords.dict_krb5_key_base64_encoded(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )
        return res


class ListenerRemoveObject(BaseModel):
    dn: str
    id: str
    udm_object_type: str
    uuid: str = None

    def __hash__(self):
        return hash(self.id)


class SchoolAuthorityConfiguration(BaseModel):
    name: str
    """name of school authority"""
    active: bool = False
    """(de)activate sending updates to this school authority"""
    url: UrlStr
    """target HTTP API URL"""
    password: SecretStr
    """password/token to access the target HTTP API"""
    mapping: Dict[str, Any] = {}
    """mapping from attribute names on the source system to attribute names on the target system"""
    passwords_target_attribute: str = None
    """attribute on the target system to write password hashes object to"""


class SchoolAuthorityConfigurationPatchDocument(BaseModel):
    active: bool = None
    """(de)activate sending updates to this school authority"""
    url: UrlStr = None
    """target HTTP API URL"""
    password: SecretStr = None
    """password/token to access the target HTTP API"""
    mapping: Dict[str, Any] = None
    """mapping from attribute names on the source system to attribute names on the target system"""
    passwords_target_attribute: str = None
    """attribute on the target system to write password hashes object to"""


class QueueModel(BaseModel):
    name: str
    head: str
    length: int
    school_authority: str = ""


class AllQueues(BaseModel):
    in_queue: QueueModel
    out_queues: List[QueueModel]


class RPCCommand(str, Enum):
    get_queue = "get_queue"
    get_queues = "get_queues"
    get_school_authority = "get_school_authority"
    get_school_authorities = "get_school_authorities"
    create_school_authority = "create_school_authority"
    delete_school_authority = "delete_school_authority"
    patch_school_authority = "patch_school_authority"


RPCCommandsRequiredArgs = {
    RPCCommand.get_queue: ("name",),
    RPCCommand.get_school_authority: ("name",),
    RPCCommand.create_school_authority: ("school_authority",),
    RPCCommand.delete_school_authority: ("name",),
    RPCCommand.patch_school_authority: ("name", "school_authority"),
}


class RPCRequest(BaseModel):
    cmd: RPCCommand
    name: str = ""
    school_authority: Dict[str, Any] = {}

    @validator("name", "school_authority", always=True, whole=True)
    def required_args_present(cls, value, values, config, field, **kwargs):
        """
        This validator will be executed for both fields. But the for loop at
        the end will make sure to only raise an exception when checking the
        corresponding field.
        """
        try:
            cmd = values["cmd"]
        except KeyError:
            return value
        try:
            required_args = RPCCommandsRequiredArgs[cmd]
        except KeyError:
            # OK: no required arguments
            return value
        for r_arg in required_args:
            if r_arg == field.name:
                if not value:
                    raise MissingArgumentError(missing_argument=r_arg)
            else:
                # raise only if we are the validator for the corresponding attribute
                continue
        return value


class RPCResponseModel(BaseModel):
    errors: List[Dict[str, Any]] = None
    result: Union[List[Any], Dict[str, Any]] = None


class User(BaseModel):
    username: str
    full_name: str = None
    disabled: bool
    dn: str
    attributes: Dict[str, List[Any]] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None


class ListenerOldDataEntry(BaseModel):
    uuid: str
    # TODO: generic attribute(s) possible?
    # source_uid: str ?
    # record_uid: str ?
    # unique_identifiers: List[Tuple[str, str]]  e.g.: [("source_uid", "abc"), ("record_uid", "xyz")]
