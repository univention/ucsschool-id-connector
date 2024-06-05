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

import logging
import os
import re
import sys
import tomllib
from functools import lru_cache
from importlib import metadata
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Any, Dict, NamedTuple, Pattern, TextIO, Union
from uuid import UUID

import base58
import colorlog

import ucsschool_id_connector

from .constants import (
    LOG_DATETIME_FORMAT,
    LOG_ENTRY_CMDLINE_FORMAT,
    LOG_ENTRY_DEBUG_FORMAT,
    LOG_FILE_PATH_QUEUES,
    PYPROJECT_FILE,
    SERVICE_NAME,
    UCR_CONTAINER_CLASS,
    UCR_CONTAINER_PUPILS,
    UCR_CONTAINER_TEACHERS,
    UCR_CONTAINER_TEACHERS_AND_STAFF,
    UCR_DB_FILE,
    UCR_GROUP_PREFIX_STUDENTS,
    UCR_GROUP_PREFIX_TEACHERS,
    UCR_REGEX,
    UCRV_LOG_LEVEL,
    UCRV_SOURCE_UID,
    UCRV_TOKEN_TTL,
)

_ucr_db_mtime = 0.0

UCRValue = Union[bool, int, str, None]


@lru_cache(maxsize=16)
def _get_ucrv_cached(ucr: str, default: UCRValue = None) -> UCRValue:
    """Cached reading of UCR values from disk."""
    try:
        with open(UCR_DB_FILE, "r") as fp:
            for line in fp:
                m = UCR_REGEX.match(line)
                if m and ucr == m.groupdict()["ucr"]:
                    return m.groupdict()["value"]
        return default
    except (KeyError, ValueError):
        return default


def get_ucrv(ucr: str, default: UCRValue = None) -> UCRValue:
    """
    Get UCR value.

    Resets cache if UCR database file has changed.
    """
    global _ucr_db_mtime

    try:
        mtime = os.stat(UCR_DB_FILE).st_mtime
    except OSError:
        return default
    if _ucr_db_mtime < mtime:
        _ucr_db_mtime = mtime
        _get_ucrv_cached.cache_clear()
    return _get_ucrv_cached(ucr, default)


def get_log_level() -> int:
    ucr_level = get_ucrv(*UCRV_LOG_LEVEL)
    if ucr_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        ucr_level = "INFO"
    return getattr(logging, ucr_level)


def get_token_ttl() -> int:
    try:
        return int(get_ucrv(*UCRV_TOKEN_TTL))
    except ValueError:
        return UCRV_TOKEN_TTL[1]


def get_source_uid() -> str:
    return get_ucrv(*UCRV_SOURCE_UID)


class ConsoleAndFileLogging:
    @classmethod
    def get_formatter(cls) -> logging.Formatter:
        return logging.Formatter(fmt=LOG_ENTRY_DEBUG_FORMAT, datefmt=LOG_DATETIME_FORMAT)

    @classmethod
    def get_stream_handler(cls, stream: TextIO = sys.stdout) -> logging.Handler:
        handler = logging.StreamHandler(stream=stream)
        handler.setFormatter(cls.get_formatter())
        return handler

    @classmethod
    def get_file_handler(cls, path: Path = LOG_FILE_PATH_QUEUES) -> logging.Handler:
        try:
            path.parent.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
        handler = WatchedFileHandler(path)
        handler.setFormatter(cls.get_formatter())
        return handler

    @classmethod
    def get_logger(cls, name: str = None, path: Path = LOG_FILE_PATH_QUEUES) -> logging.Logger:
        logger = logging.getLogger(name or SERVICE_NAME)
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            logger.addHandler(cls.get_stream_handler())
        if not any(isinstance(handler, WatchedFileHandler) for handler in logger.handlers):
            logger.addHandler(cls.get_file_handler(path))
        logger.setLevel(get_log_level())
        return logger

    @classmethod
    def add_console_handler(cls, logger):
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(LOG_ENTRY_CMDLINE_FORMAT))
        logger.addHandler(handler)


class RegExpsGroups(NamedTuple):
    domain_users_ou: Pattern
    lehrer_ou: Pattern
    schueler_ou: Pattern
    school_class: Pattern
    workgroup: Pattern


class RegExpsUsers(NamedTuple):
    student: Pattern
    teacher: Pattern
    teacher_and_staff: Pattern


@lru_cache(maxsize=1)
def domain_users_ou_dn_regex() -> Pattern:
    """Regex to match 'cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    return re.compile(
        f"cn=Domain Users (?P<ou>.+?),cn=groups,ou=(?P=ou),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def lehrer_ou_dn_regex() -> Pattern:
    """Regex to match 'cn=lehrer-demoschool,cn=groups,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    # default value of env.get("ucsschool_ldap_default_...") can be the
    # empty string, because of the apps 'env' file
    prefix_teacher = os.environ.get(UCR_GROUP_PREFIX_TEACHERS[0]) or UCR_GROUP_PREFIX_TEACHERS[1]
    return re.compile(
        f"cn={prefix_teacher}(?P<ou>.+?),cn=groups,ou=(?P=ou),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def schueler_ou_dn_regex() -> Pattern:
    """Regex to match 'cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    prefix_students = os.environ.get(UCR_GROUP_PREFIX_STUDENTS[0]) or UCR_GROUP_PREFIX_STUDENTS[1]
    return re.compile(
        f"cn={prefix_students}(?P<ou>.+?),cn=groups,ou=(?P=ou),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def school_class_dn_regex() -> Pattern:
    """Regex to match 'cn=DEMOSCHOOL-1a,cn=klassen,cn=schueler,cn=groups,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    c_class = os.environ.get(UCR_CONTAINER_CLASS[0]) or UCR_CONTAINER_CLASS[1]
    c_student = os.environ.get(UCR_CONTAINER_PUPILS[0]) or UCR_CONTAINER_PUPILS[1]
    return re.compile(
        f"cn=(?P<ou>[^,]+?)-(?P<name>[^,]+?),"
        f"cn={c_class},cn={c_student},cn=groups,"
        f"ou=(?P=ou),"
        f"{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def student_dn_regex() -> Pattern:
    """Regex to match 'uid=demo_student,cn=schueler,cn=users,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    c_student = os.environ.get(UCR_CONTAINER_PUPILS[0]) or UCR_CONTAINER_PUPILS[1]
    return re.compile(
        f"uid=(?P<name>.+?),cn={c_student},cn=users,ou=(?P<ou>.+?),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def teacher_dn_regex() -> Pattern:
    """Regex to match 'uid=demo_teacher,cn=lehrer,cn=users,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    c_teachers = os.environ.get(UCR_CONTAINER_TEACHERS[0]) or UCR_CONTAINER_TEACHERS[1]
    return re.compile(
        f"uid=(?P<name>.+?),cn={c_teachers},cn=users,ou=(?P<ou>.+?),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def teacher_and_staff_dn_regex() -> Pattern:
    """Regex to match 'uid=demo_teachstaff,cn=lehrer und mitarbeiter,cn=users,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    c_teacher_staff = (
        os.environ.get(UCR_CONTAINER_TEACHERS_AND_STAFF[0]) or UCR_CONTAINER_TEACHERS_AND_STAFF[1]
    )
    return re.compile(
        f"uid=(?P<name>.+?),cn={c_teacher_staff},cn=users,ou=(?P<ou>.+?),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def workgroup_dn_regex() -> Pattern:
    """Regex to match 'cn=DEMOSCHOOL-wg1,cn=schueler,cn=groups,ou=DEMOSCHOOL,...'."""
    base_dn = os.environ["ldap_base"]
    c_student = os.environ.get(UCR_CONTAINER_PUPILS[0]) or UCR_CONTAINER_PUPILS[1]
    return re.compile(
        f"cn=(?P<ou>[^,]+?)-(?P<name>[^,]+?),cn={c_student},cn=groups,ou=(?P=ou),{base_dn}",
        flags=re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def kelvin_url_regex() -> Pattern:
    return re.compile(r"^https://(?P<host>.+?)/ucsschool/kelvin/v(?P<version>.+?)/?")


@lru_cache(maxsize=1)
def ucsschool_role_regex() -> Pattern:
    return re.compile(r"^(?P<role>[^:]+):(?P<context_type>[^:]+):(?P<context>[^:]+)$")


@lru_cache(maxsize=1)
def get_app_version() -> str:

    v = metadata.version(ucsschool_id_connector.__name__)
    # if the module is available but not installed, it is reported as 0.0.0
    if v == "0.0.0":
        with open(Path(__file__).parent.parent / PYPROJECT_FILE, "rb") as fp:
            project_data = tomllib.load(fp)
        return project_data["tool"]["poetry"]["version"]
    else:
        return v


def entry_uuid_to_base58(entry_uuid: str) -> str:
    uuid = UUID(entry_uuid)
    b58_b = base58.b58encode_int(uuid.int)
    return b58_b.decode()


def base58_to_entry_uuid(b58_s: str) -> str:
    uuid_as_int = base58.b58decode_int(b58_s)
    uuid = UUID(int=uuid_as_int)
    return str(uuid)


def recursive_dict_update(
    ori: Dict[Any, Any], updater: Dict[Any, Any], update_none_values: bool = True
) -> Dict[Any, Any]:
    """
    *In-place* update the dict `ori` with the content of `updater`.

    :param dict ori: dict to change
    :param dict updater: data to change in `ori`
    :return: the changed `ori` - beware: the change is done *in-place*, this
        return value is only for convenience
    :raises ValueError: if an existing dict in `ori` should be overwritten by a
        non-dict
    """

    for k, v in updater.items():
        if isinstance(ori.get(k), dict):
            if not isinstance(v, dict):
                raise ValueError(f"Cannot update dict from non-dict: k={k!r} ori={ori!r} v={v!r}")
            recursive_dict_update(ori=ori[k], updater=v, update_none_values=update_none_values)
        else:
            if v is not None or update_none_values:
                ori[k] = v
    return ori
