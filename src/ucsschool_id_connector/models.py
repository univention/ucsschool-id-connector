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

import abc
import base64
import logging
import re
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, Union

import lazy_object_proxy
from pydantic import AnyUrl, BaseModel, PydanticValueError, SecretStr, validator

if TYPE_CHECKING:  # pragma: no cover
    from pydantic.main import Model

from .utils import ConsoleAndFileLogging

# for debugging during coding
logger: logging.Logger = lazy_object_proxy.Proxy(lambda: ConsoleAndFileLogging.get_logger(__name__))


class ListenerFileAttributeError(PydanticValueError):
    code = "invalid_listener_file"
    msg_template = 'Missing or empty value in listener file: "{key}"="{value}"'


class MissingDefaultUdmOptionError(ListenerFileAttributeError):
    msg_template = 'Missing "default" in UDM options: "{key}"="{value}"'


class MissingSchoolUserObjectClassError(ListenerFileAttributeError):
    msg_template = 'No UCS@school user object class: "{key}"="{value}"'


class MissingSchoolAttributeError(ListenerFileAttributeError):
    msg_template = 'Missing or empty "school" attribute: "{key}"="{value}"'


class UnsupportedUdmObjectTypeError(ListenerFileAttributeError):
    msg_template = 'Unsupported UDM object type: "{key}"="{value}"'


class MissingArgumentError(PydanticValueError):
    code = "missing_argument"
    msg_template = 'value is missing or empty "{missing_argument}"'


class NoObjectError(PydanticValueError):
    code = "no_object"
    msg_template = 'no object found with "{key}"="{value}"'


class ObjectExistsError(PydanticValueError):
    code = "object_exists"
    msg_template = 'object with "{key}"="{value}" already exists'


class SchoolUserRole(str, Enum):
    staff = "staff"
    student = "student"
    teacher = "teacher"


class UnknownSchoolUserRole(Exception):
    def __init__(self, *args, roles: List[str] = None, **kwargs):
        self.roles = roles
        super().__init__(*args, **kwargs)


class ListenerOldDataEntry(BaseModel, abc.ABC):
    ...


class ListenerGroupOldDataEntry(ListenerOldDataEntry):
    users: List[str]

    def __repr__(self):
        num_users = len(self.users)
        if num_users > 5:
            users_str = f"{num_users} members: [...]"
        else:
            users_str = f"{num_users} members: {self.users!r}"
        return f"{self.__class__.__name__}({users_str})"


class ListenerUserOldDataEntry(ListenerOldDataEntry):
    schools: List[str]
    record_uid: str = None
    source_uid: str = None

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(school={self.schools!r}, record_uid="
            f"{self.record_uid!r}, source_uid={self.source_uid!r})"
        )


class UserPasswords(BaseModel):
    userPassword: List[str]
    sambaNTPassword: str
    krb5Key: List[bytes]
    krb5KeyVersionNumber: int
    sambaPwdLastSet: int

    def __eq__(self, other: Any):
        if not isinstance(other, UserPasswords):
            return False
        return (
            set(self.userPassword) == set(other.userPassword)
            and self.sambaNTPassword == other.sambaNTPassword
            and set(self.krb5Key) == set(other.krb5Key)
            and self.krb5KeyVersionNumber == other.krb5KeyVersionNumber
            and self.sambaPwdLastSet == other.sambaPwdLastSet
        )

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


class ListenerActionEnum(str, Enum):
    add_mod = "add_mod"
    delete = "delete"


class ListenerObject(BaseModel, abc.ABC):
    dn: str
    id: str
    udm_object_type: str
    action: ListenerActionEnum = None

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.udm_object_type!r}, {self.dn!r})"


class ListenerAddModifyObject(ListenerObject, abc.ABC):
    object: Dict[str, Any]
    options: List[str]
    action = ListenerActionEnum.add_mod
    old_data: ListenerOldDataEntry = None

    @validator("udm_object_type")
    def supported_udm_object_type(cls, value):
        raise NotImplementedError("Implement this in a subclass specific for each UDM object type.")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.udm_object_type!r}, {self.dn!r}, {self.old_data!r})"


class ListenerGroupAddModifyObject(ListenerAddModifyObject):
    old_data: ListenerGroupOldDataEntry = None

    @validator("udm_object_type")
    def supported_udm_object_type(cls, value):
        if value != "groups/group":
            raise UnsupportedUdmObjectTypeError(key="udm_object_type", value=value)
        return value

    @property
    def name(self) -> str:
        return self.object["name"]

    @property
    def users(self) -> List[str]:
        return self.object["users"]


class ListenerUserAddModifyObject(ListenerAddModifyObject):
    user_passwords: UserPasswords = None
    old_data: ListenerUserOldDataEntry = None

    @validator("udm_object_type")
    def supported_udm_object_type(cls, value):
        if value != "users/user":
            raise UnsupportedUdmObjectTypeError(key="udm_object_type", value=value)
        return value

    @validator("options", whole=True)
    def has_required_oc(cls, value):
        options = set(value)
        if not {"default"}.intersection(options):
            raise MissingDefaultUdmOptionError(key="options", value=value)
        if not {"ucsschoolStaff", "ucsschoolStudent", "ucsschoolTeacher"}.intersection(options):
            raise MissingSchoolUserObjectClassError(key="options", value=value)
        return value

    @validator("object", whole=True)
    def has_required_attrs(cls, value):
        if not value.get("school"):
            raise MissingSchoolAttributeError(key="object", value=value)
        return value

    @property
    def record_uid(self) -> Optional[str]:
        return self.object.get("ucsschoolRecordUID")

    @property
    def source_uid(self) -> Optional[str]:
        return self.object.get("ucsschoolSourceUID")

    @property
    def school(self) -> str:
        try:
            ou_from_dn = re.match(r".+,ou=(.+?),dc=.+", self.dn).groups()[0]
        except (AttributeError, IndexError):
            logger.error("Failed to find OU in dn %r.", self.dn)
        else:
            if ou_from_dn in self.object["school"]:
                return ou_from_dn
            else:
                logger.error(
                    "OU found in DN (%r) not in 'school' attribute (%r) of user with " "DN %r.",
                    ou_from_dn,
                    self.object["school"],
                    self.dn,
                )
        return sorted(self.object["school"])[0]

    @property
    def schools(self) -> List[str]:
        return self.object["school"]

    @property
    def school_user_roles(self) -> List[SchoolUserRole]:
        options = set(self.options)
        if options >= {"ucsschoolTeacher", "ucsschoolStaff"}:
            return [SchoolUserRole.staff, SchoolUserRole.teacher]
        if "ucsschoolTeacher" in options:
            return [SchoolUserRole.teacher]
        if "ucsschoolStaff" in options:
            return [SchoolUserRole.staff]
        if "ucsschoolStudent" in options:
            return [SchoolUserRole.student]
        # administrator and exam_user are not supported
        raise UnknownSchoolUserRole(f"Unknown or missing school user type in options: {self.options!r}")

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
        """wrapper around :py:meth:`dict()` that base64 encodes
        `user_passwords.krb5Key`"""
        res = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )
        if self.user_passwords:
            res["user_passwords"] = self.user_passwords.dict_krb5_key_base64_encoded(
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                skip_defaults=skip_defaults,
            )
        return res


class ListenerRemoveObject(ListenerObject, abc.ABC):
    action = ListenerActionEnum.delete


class ListenerGroupRemoveObject(ListenerRemoveObject):
    old_data: ListenerGroupOldDataEntry = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.udm_object_type!r}, {self.dn!r}, {self.old_data!r})"


class ListenerUserRemoveObject(ListenerRemoveObject):
    old_data: ListenerUserOldDataEntry = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.udm_object_type!r}, {self.dn!r}, {self.old_data!r})"


class SecretsMixin:
    def __init__(self, **data: Any) -> None:
        super(SecretsMixin, self).__init__(**data)
        # when passed into a HTTP resource, parse_obj() is not called
        if self.plugin_configs:
            self.plugin_configs_plain_to_secret(self.plugin_configs)

    def dict_secrets_as_str(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Same as `.dict()` but values of `key`, `password`, `token` in
        `plugin_configs` will be plain str.
        """
        res = self.dict(*args, **kwargs)
        if res["plugin_configs"]:
            self.plugin_configs_secrets_to_plain(res["plugin_configs"])
        return res

    @staticmethod
    def plugin_configs_secrets_to_plain(plugin_configs: Dict[str, Dict[str, Any]]) -> None:
        """
        In-place modification of secret values in `plugin_configs` SecretStr -> str.
        """
        for plugin_name, plugin_config in plugin_configs.items():
            for key, value in plugin_config.items():
                if key in ("key", "password", "token") and isinstance(value, SecretStr):
                    plugin_configs[plugin_name][key] = value.get_secret_value()

    @staticmethod
    def plugin_configs_plain_to_secret(plugin_configs: Dict[str, Dict[str, Any]]) -> None:
        """
        In-place modification of secret values in `plugin_configs` str -> SecretStr.
        """
        for plugin_name, plugin_config in plugin_configs.items():
            for key, value in plugin_config.items():
                if key in ("key", "password", "token") and isinstance(value, str):
                    plugin_configs[plugin_name][key] = SecretStr(value)

    @classmethod
    def parse_obj(cls: Type["Model"], obj: Any) -> "Model":
        res: SchoolAuthorityConfiguration = super(SecretsMixin, cls).parse_obj(obj)
        if res.plugin_configs:
            cls.plugin_configs_plain_to_secret(res.plugin_configs)
        return res


class SchoolAuthorityConfiguration(SecretsMixin, BaseModel):
    name: str
    """name of school authority"""
    active: bool = False
    """(de)activate sending updates to this school authority"""
    url: AnyUrl
    """target HTTP API URL"""
    plugins: List[str] = []
    """the plugins that should be executed for this specific school
    authority during handling in the out queue"""
    plugin_configs: Dict[str, Dict[str, Any]]
    """Plugin specific configurations,
    e.g. {
        "kelvin": {
            "mapping": { .. },
            "username": "..",
            "password": "..",
            "sync_password_hashes": ".."
        },
    }
    Attention: values for keys named `key`, `password` or `token` will be converted to SecretStr.
    """


class SchoolAuthorityConfigurationPatchDocument(SecretsMixin, BaseModel):
    active: bool = None
    """(de)activate sending updates to this school authority"""
    url: AnyUrl = None
    """target HTTP API URL"""
    plugins: List[str] = None
    """the plugins that should be executed for this specific school
    authority during handling in the out queue"""
    plugin_configs: Dict[str, Dict[str, Any]] = None
    """Plugin specific configurations,
    e.g. {
        "kelvin": {"username": "..", "password": "..", "sync_password_hashes": ".."},
    }
    Attention: values for keys named `key`, `password` or `token` will be converted to SecretStr.
    """


class School2SchoolAuthorityMapping(BaseModel):
    mapping: Dict[str, str]
    """Keys are OUs, values are `name` of SchoolAuthorityConfiguration objects"""


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
    get_school_to_authority_mapping = "get_school_to_authority_mapping"
    create_school_authority = "create_school_authority"
    delete_school_authority = "delete_school_authority"
    patch_school_authority = "patch_school_authority"
    put_school_to_authority_mapping = "put_school_to_authority_mapping"


RPCCommandsRequiredArgs = {
    RPCCommand.get_queue: ("name",),
    RPCCommand.get_school_authority: ("name",),
    RPCCommand.create_school_authority: ("school_authority",),
    RPCCommand.delete_school_authority: ("name",),
    RPCCommand.patch_school_authority: ("name", "school_authority"),
    RPCCommand.put_school_to_authority_mapping: ("school_to_authority_mapping",),
}


class RPCRequest(BaseModel):
    cmd: RPCCommand
    name: str = ""
    school_authority: Dict[str, Any] = {}
    school_to_authority_mapping: Dict[str, Any] = {}

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
            if r_arg == field.name and not value:
                raise MissingArgumentError(missing_argument=r_arg)
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


class Group(BaseModel):
    groupname: str
    dn: str
    attributes: Dict[str, List[Any]] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None
