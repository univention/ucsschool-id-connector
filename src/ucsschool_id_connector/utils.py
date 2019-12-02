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

import logging
import os
import re
from functools import lru_cache
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import TextIO, Union

import aiofiles
import colorlog
from async_lru import alru_cache

from .constants import (
    DOCKER_LOG_FD,
    LOG_DATETIME_FORMAT,
    LOG_ENTRY_CMDLINE_FORMAT,
    LOG_ENTRY_DEBUG_FORMAT,
    LOG_FILE_PATH_QUEUES,
    SERVICE_NAME,
    UCR_CONTAINER_CLASS,
    UCR_CONTAINER_PUPILS,
    UCR_DB_FILE,
    UCR_REGEX,
    UCRV_SOURCE_UID,
    UCRV_TOKEN_TTL,
)

_ucr_db_mtime = 0

UCRValue = Union[bool, int, str, None]


@alru_cache(maxsize=4)
async def _get_ucrv_cached(ucr: str, default: UCRValue = None) -> UCRValue:
    """Cached reading of UCR values from disk."""
    try:
        async with aiofiles.open(UCR_DB_FILE, "r") as fp:
            async for line in fp:
                m = UCR_REGEX.match(line)
                if m and ucr == m.groupdict()["ucr"]:
                    return m.groupdict()["value"]
        return default
    except (KeyError, ValueError):
        return default


async def close_ucr_cache():
    await _get_ucrv_cached.close()


async def get_ucrv(ucr: str, default: UCRValue = None) -> UCRValue:
    """
    Get UCR value.

    Resets cache if UCR database has changed.
    """
    global _ucr_db_mtime

    mtime = os.stat(UCR_DB_FILE).st_mtime
    if _ucr_db_mtime < mtime:
        _ucr_db_mtime = mtime
        _get_ucrv_cached.cache_clear()
    return await _get_ucrv_cached(ucr, default)


async def get_token_ttl() -> int:
    try:
        return int(await get_ucrv(*UCRV_TOKEN_TTL))
    except ValueError:
        return UCRV_TOKEN_TTL[1]


async def get_source_uid() -> str:
    return await get_ucrv(*UCRV_SOURCE_UID)


class ConsoleAndFileLogging:
    @classmethod
    def get_formatter(cls) -> logging.Formatter:
        return logging.Formatter(
            fmt=LOG_ENTRY_DEBUG_FORMAT, datefmt=LOG_DATETIME_FORMAT
        )

    @classmethod
    def get_stream_handler(cls, stream: TextIO = DOCKER_LOG_FD) -> logging.Handler:
        handler = logging.StreamHandler(stream=stream)
        handler.setFormatter(cls.get_formatter())
        return handler

    @classmethod
    def get_file_handler(cls, path: Path = LOG_FILE_PATH_QUEUES) -> logging.Handler:
        try:
            path.parent.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
        handler = TimedRotatingFileHandler(path, when="W0", backupCount=15)
        handler.setFormatter(cls.get_formatter())
        return handler

    @classmethod
    def get_logger(
        cls, name: str = None, path: Path = LOG_FILE_PATH_QUEUES
    ) -> logging.Logger:
        logger = logging.getLogger(name or SERVICE_NAME)
        if not any(
            isinstance(handler, logging.StreamHandler) for handler in logger.handlers
        ):
            logger.addHandler(cls.get_stream_handler())
        if not any(
            isinstance(handler, TimedRotatingFileHandler) for handler in logger.handlers
        ):
            logger.addHandler(cls.get_file_handler(path))
        logger.setLevel(logging.DEBUG)
        return logger

    @classmethod
    def add_console_handler(cls, logger):
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(LOG_ENTRY_CMDLINE_FORMAT))
        logger.addHandler(handler)


@lru_cache(maxsize=1)
def class_dn_regex():
    base_dn = os.environ["ldap_base"]
    # default value of env.get("ucsschool_ldap_default_...") can be the
    # empty string, because of the apps 'env' file
    c_class = os.environ.get(UCR_CONTAINER_CLASS[0]) or UCR_CONTAINER_CLASS[1]
    c_student = os.environ.get(UCR_CONTAINER_PUPILS[0]) or UCR_CONTAINER_PUPILS[1]
    return re.compile(
        f"cn=(?P<ou>.+?)-(?P<name>.+?),"
        f"cn={c_class},cn={c_student},cn=groups,"
        f"ou=(?P=ou),"
        f"{base_dn}",
        flags=re.IGNORECASE,
    )