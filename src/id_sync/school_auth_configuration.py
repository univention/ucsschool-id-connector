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
import pprint
from typing import AsyncIterator, Iterable, Iterator

import aiofiles
import lazy_object_proxy
import ujson
from pydantic import ValidationError

from .constants import LOG_FILE_PATH_QUEUES, SCHOOL_AUTHORITIES_CONFIG_PATH
from .models import SchoolAuthorityConfiguration
from .utils import ConsoleAndFileLogging


class Configuration:
    logger: logging.Logger = lazy_object_proxy.Proxy(
        lambda: ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_QUEUES)
    )

    @classmethod
    async def load_school_authorities(
        cls
    ) -> AsyncIterator[SchoolAuthorityConfiguration]:
        cls.logger.debug(
            "Looking for configuration in %s...", SCHOOL_AUTHORITIES_CONFIG_PATH
        )
        cls.mkdir_config_path()
        with os.scandir(
            SCHOOL_AUTHORITIES_CONFIG_PATH
        ) as dir_entries:  # type: Iterator[os.DirEntry]
            for entry in dir_entries:
                if not entry.is_file() or not entry.name.lower().endswith(".json"):
                    cls.logger.warning(
                        "Non-JSON file found in configuration directory %r: %r.",
                        SCHOOL_AUTHORITIES_CONFIG_PATH,
                        entry.name,
                    )
                    continue
                cls.logger.debug("Loading configuration %r...", entry.name)
                try:
                    async with aiofiles.open(entry.path, "r") as fp:
                        obj = ujson.loads(await fp.read())
                    school_authority = SchoolAuthorityConfiguration.parse_obj(obj)
                    school_authority.url.rstrip("/")
                    cls.logger.info(
                        "Loaded SchoolAuthorityConfiguration:\n%s",
                        pprint.pformat(school_authority.dict()),
                    )
                    yield school_authority
                except (IOError, OSError, ValueError, ValidationError) as exc:
                    cls.logger.error(
                        "Error loading configuration file %r: %s", entry.path, exc
                    )
                    continue

    @classmethod
    async def save_school_authorities(
        cls, school_authority_configs: Iterable[SchoolAuthorityConfiguration]
    ) -> None:
        cls.mkdir_config_path()
        for config in school_authority_configs:
            config.url.rstrip("/")
            path = SCHOOL_AUTHORITIES_CONFIG_PATH / f"{config.name}.json"
            cls.logger.info("Writing configuration of %r to %s...", config.name, path)
            config_as_dict = config.dict()
            config_as_dict["password"] = config.password.get_secret_value()
            async with aiofiles.open(path, "w") as fp:
                await fp.write(ujson.dumps(config_as_dict, indent=4))

    @classmethod
    async def delete_school_authority(cls, name: str) -> None:
        cls.mkdir_config_path()
        path = SCHOOL_AUTHORITIES_CONFIG_PATH / f"{name}.json"
        if path.exists() and not path.is_file():
            cls.logger.error("Not a file: %s", path)
        else:
            try:
                path.unlink()
                cls.logger.info("Deleted configuration file %s.", path)
            except FileNotFoundError:
                pass
            except (IOError, OSError) as exc:
                cls.logger.error("Error deleting configuration file %s: %s", path, exc)

    @classmethod
    def mkdir_config_path(cls):
        try:
            SCHOOL_AUTHORITIES_CONFIG_PATH.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
