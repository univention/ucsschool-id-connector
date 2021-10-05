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

import os
from collections import namedtuple
from datetime import datetime
from typing import List, Optional

import aiofiles
import lazy_object_proxy
from ldap3 import AUTO_BIND_TLS_BEFORE_BIND, SIMPLE, Connection, Entry, Server
from ldap3.core.exceptions import LDAPBindError, LDAPExceptionError
from ldap3.utils.conv import escape_filter_chars

from .constants import ADMIN_GROUP_NAME, LOG_FILE_PATH_HTTP, MACHINE_PASSWORD_FILE
from .models import User, UserPasswords
from .utils import ConsoleAndFileLogging

MachinePWCache = namedtuple("MachinePWCache", ["mtime", "password"])


class LDAPAccess:
    host_dn: str = lazy_object_proxy.Proxy(lambda: os.environ["ldap_hostdn"])
    _machine_pw = MachinePWCache(0, "")

    def __init__(self, host: str = None, port: int = None, ldap_base: str = None):
        self.ldap_base = ldap_base or os.environ["ldap_base"]
        self.logger = ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_HTTP)
        self.server = Server(
            host=host or os.environ["ldap_server_name"],
            port=port or int(os.environ["ldap_server_port"]),
            get_info="ALL",
        )

    @classmethod
    async def machine_password(cls) -> str:
        mtime = os.stat(MACHINE_PASSWORD_FILE).st_mtime
        if cls._machine_pw.mtime == mtime:
            return cls._machine_pw.password
        else:
            async with aiofiles.open(MACHINE_PASSWORD_FILE, "r") as fp:
                pw = await fp.read()
                pw = pw.strip()
            cls._machine_pw = MachinePWCache(mtime, pw)
            return pw

    def check_auth_dn(self, bind_dn: str, bind_pw: str) -> bool:
        try:
            with Connection(
                self.server,
                user=bind_dn,
                password=bind_pw,
                auto_bind=AUTO_BIND_TLS_BEFORE_BIND,
                authentication=SIMPLE,
                read_only=True,
            ):
                self.logger.info("Successful LDAP: %r.", bind_dn)
                return True
        except LDAPBindError:
            self.logger.info("Invalid credentials for %r.", bind_dn)
            return False
        except LDAPExceptionError as exc:
            self.logger.exception(
                "When connecting to %r with bind_dn %r: %s",
                self.server.host,
                bind_dn,
                exc,
            )
            return False

    async def check_auth_and_get_user(self, username: str, password: str) -> Optional[User]:
        user_dn = await self.get_dn_of_user(username)
        if user_dn:
            admin_group_members = await self.admin_group_members()
            if user_dn in admin_group_members:
                return await self.get_user(username, user_dn, password, school_only=False)
            else:
                self.logger.debug("User %r not member of group %r.", username, ADMIN_GROUP_NAME)
                return None
        else:
            self.logger.debug("No such user in LDAP: %r.", username)
            return None

    async def search(
        self,
        filter_s: str,
        attributes: List[str] = None,
        base: str = None,
        bind_dn: str = None,
        bind_pw: str = None,
        raise_on_bind_error: bool = True,
    ) -> List[Entry]:
        base = base or self.ldap_base
        bind_dn = bind_dn or self.host_dn
        bind_pw = bind_pw or await self.machine_password()
        try:
            with Connection(
                self.server,
                user=bind_dn,
                password=bind_pw,
                auto_bind=AUTO_BIND_TLS_BEFORE_BIND,
                authentication=SIMPLE,
                read_only=True,
            ) as conn:
                conn.search(base, filter_s, attributes=attributes)
        except LDAPExceptionError as exc:
            if isinstance(exc, LDAPBindError) and not raise_on_bind_error:
                return []
            self.logger.exception(
                "When connecting to %r with bind_dn %r: %s",
                self.server.host,
                self.host_dn,
                exc,
            )
            raise
        return conn.entries

    async def get_dn_of_user(self, username: str) -> str:
        filter_s = f"(uid={escape_filter_chars(username)})"
        results = await self.search(filter_s, attributes=None)
        if len(results) == 1:
            return results[0].entry_dn
        elif len(results) > 1:
            raise RuntimeError(
                f"More than 1 result when searching LDAP with filter {filter_s!r}: {results!r}."
            )
        else:
            return ""

    async def get_passwords(
        self,
        username: str,
        base: str = None,
        bind_dn: str = None,
        bind_pw: str = None,
    ) -> Optional[UserPasswords]:
        filter_s = f"(uid={escape_filter_chars(username)})"
        attributes = [
            "krb5Key",
            "krb5KeyVersionNumber",
            "sambaPwdLastSet",
            "sambaNTPassword",
            "userPassword",
        ]
        results = await self.search(filter_s, attributes, base=base, bind_dn=bind_dn, bind_pw=bind_pw)
        if len(results) == 1:
            result = results[0]
            return UserPasswords(
                userPassword=result["userPassword"].values,
                sambaNTPassword=result["sambaNTPassword"].value,
                krb5Key=result["krb5Key"].values,
                krb5KeyVersionNumber=result["krb5KeyVersionNumber"].value,
                sambaPwdLastSet=result["sambaPwdLastSet"].value,
            )
        elif len(results) > 1:
            raise RuntimeError(
                f"More than 1 result when searching LDAP with filter {filter_s!r}: {results!r}."
            )
        else:
            return None

    @staticmethod
    def user_is_disabled(ldap_result):
        return (
            "D" in ldap_result["sambaAcctFlags"].value
            or ldap_result["krb5KDCFlags"].value == 254
            or (
                "shadowExpire" in ldap_result
                and ldap_result["shadowExpire"].value
                and ldap_result["shadowExpire"].value < datetime.now().timestamp() / 3600 / 24
            )
        )

    async def get_user(
        self,
        username: str,
        bind_dn: str = None,
        bind_pw: str = None,
        attributes: List[str] = None,
        school_only=True,
    ) -> Optional[User]:
        if attributes:
            attributes = attributes + [
                "displayName",
                "krb5KDCFlags",
                "sambaAcctFlags",
                "shadowExpire",
                "uid",
            ]
        else:
            attributes = [
                "displayName",
                "krb5KDCFlags",
                "sambaAcctFlags",
                "shadowExpire",
                "uid",
            ]
        filter_s = f"(uid={escape_filter_chars(username)})"
        if school_only:
            filter_s = (
                f"(&{filter_s}(|"
                f"(objectClass=ucsschoolStaff)"
                f"(objectClass=ucsschoolStudent)"
                f"(objectClass=ucsschoolTeacher)"
                f"))"
            )
        results = await self.search(
            filter_s,
            attributes,
            bind_dn=bind_dn,
            bind_pw=bind_pw,
            raise_on_bind_error=False,
        )
        if len(results) == 1:
            result = results[0]
            return User(
                username=result["uid"].value,
                full_name=result["displayName"].value,
                disabled=self.user_is_disabled(result),
                dn=result.entry_dn,
                attributes=result.entry_attributes_as_dict,
            )
        elif len(results) > 1:
            raise RuntimeError(
                f"More than 1 result when searching LDAP with filter {filter_s!r}: {results!r}."
            )
        else:
            return None

    async def admin_group_members(self) -> List[str]:
        filter_s = f"(cn={escape_filter_chars(ADMIN_GROUP_NAME)})"
        base = f"cn=groups,{self.ldap_base}"
        results = await self.search(filter_s, ["uniqueMember"], base=base)
        if len(results) == 1:
            return results[0]["uniqueMember"].values
        else:
            self.logger.error("Reading %r from LDAP: results=%r", ADMIN_GROUP_NAME, results)
            return []

    async def extended_attribute_ldap_mapping(self, udm_property_name: str) -> Optional[str]:
        filter_s = f"(&(objectClass=univentionUDMProperty)(cn={escape_filter_chars(udm_property_name)}))"
        base = f"cn=custom attributes,cn=univention,{self.ldap_base}"
        results = await self.search(filter_s, ["univentionUDMPropertyLdapMapping"], base=base)
        if len(results) == 1:
            return results[0]["univentionUDMPropertyLdapMapping"].value
        else:
            self.logger.error("Reading %r from LDAP: results=%r", udm_property_name, results)
            return None
