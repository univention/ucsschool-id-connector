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
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import TextIO, Union

import aiofiles
import colorlog
from async_lru import alru_cache
from diskcache import Cache

from .constants import (
    DOCKER_LOG_FD,
    LOG_DATETIME_FORMAT,
    LOG_ENTRY_CMDLINE_FORMAT,
    LOG_ENTRY_DEBUG_FORMAT,
    LOG_FILE_PATH_QUEUES,
    SERVICE_NAME,
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
        return int(await get_ucrv(UCRV_TOKEN_TTL, 60))
    except ValueError:
        return 60


async def get_source_uid() -> str:
    return await get_ucrv(UCRV_SOURCE_UID, "TESTID")


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


class KeyValueDB:
    def __init__(self, datebase_dir: Path):
        if not datebase_dir.exists():
            datebase_dir.mkdir(mode=0o750, parents=True)
        self._cache = Cache(str(datebase_dir))

    def __contains__(self, key):
        return self._cache.__contains__(key)

    def __delitem__(self, key):
        return self._cache.__delitem__(key)

    def __getitem__(self, key):
        return self._cache.__getitem__(key)

    def __setitem__(self, key, value):
        return self._cache.__setitem__(key, value)

    def close(self, *args, **kwargs):
        return self._cache.close()

    def get(self, key, default=None, *args, **kwargs):
        return self._cache.get(key, default, *args, **kwargs)

    def set(self, key, value, *args, **kwargs):
        return self._cache.set(key, value, *args, **kwargs)

    def touch(self, *args, **kwargs):
        return self._cache.touch(*args, **kwargs)
