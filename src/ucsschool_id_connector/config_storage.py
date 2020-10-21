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
import pprint
from pathlib import Path
from typing import AsyncIterator, Iterable, Iterator, cast

import aiofiles
import lazy_object_proxy
import ujson
from pydantic import ValidationError

from .constants import (
    LOG_FILE_PATH_QUEUES,
    SCHOOL_AUTHORITIES_CONFIG_PATH,
    SCHOOLS_TO_AUTHORITIES_MAPPING_PATH,
)
from .models import School2SchoolAuthorityMapping, SchoolAuthorityConfiguration
from .utils import ConsoleAndFileLogging


class SchoolMappingLoadingError(Exception):
    pass


class SchoolAuthorityConfigurationLoadingError(Exception):
    pass


class ConfigurationStorage:
    logger: logging.Logger = lazy_object_proxy.Proxy(
        lambda: ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_QUEUES)
    )

    @classmethod
    def school_authority_config_files(cls) -> Iterator[Path]:
        cls.logger.debug("Looking for configuration in %s...", SCHOOL_AUTHORITIES_CONFIG_PATH)
        cls.mkdir_p(SCHOOL_AUTHORITIES_CONFIG_PATH)
        with os.scandir(SCHOOL_AUTHORITIES_CONFIG_PATH) as dir_entries:
            dir_entries = cast(Iterator[os.DirEntry], dir_entries)
            for entry in dir_entries:
                if not entry.is_file() or not entry.name.lower().endswith(".json"):
                    cls.logger.warning(
                        "Non-JSON file found in configuration directory %r: %r.",
                        SCHOOL_AUTHORITIES_CONFIG_PATH,
                        entry.name,
                    )
                    continue
                yield Path(entry.path)

    @classmethod
    async def load_school_authority(cls, path: Path) -> SchoolAuthorityConfiguration:
        """
        May raise IOError, OSError, ValueError or ValidationError.
        """
        cls.logger.debug("Loading configuration %r...", path.name)
        async with aiofiles.open(path, "r") as fp:
            obj = ujson.loads(await fp.read())
        school_authority = SchoolAuthorityConfiguration.parse_obj(obj)
        cls.logger.info(
            "Loaded school authority configuration:\n%s",
            pprint.pformat(school_authority.dict()),
        )
        return school_authority

    @classmethod
    async def load_school_authorities(
        cls,
    ) -> AsyncIterator[SchoolAuthorityConfiguration]:
        """May raise SchoolAuthorityConfigurationLoadingError."""
        for path in cls.school_authority_config_files():
            try:
                yield await cls.load_school_authority(path)
            except (IOError, OSError, ValueError, ValidationError) as exc:
                cls.logger.error("Error loading configuration file %r: %s", str(path), exc)
                raise SchoolAuthorityConfigurationLoadingError(str(exc)) from exc

    @classmethod
    async def save_school_authorities(
        cls, school_authority_configs: Iterable[SchoolAuthorityConfiguration]
    ) -> None:
        cls.mkdir_p(SCHOOL_AUTHORITIES_CONFIG_PATH)
        for config in school_authority_configs:
            path = SCHOOL_AUTHORITIES_CONFIG_PATH / f"{config.name}.json"
            await cls.save_school_authority(config, path)

    @classmethod
    async def save_school_authority(
        cls,
        config: SchoolAuthorityConfiguration,
        path: Path,
    ) -> None:
        cls.mkdir_p(path.parent)
        cls.logger.info("Writing configuration of %r to %s...", config.name, path)
        config_as_dict = config.dict()
        config_as_dict["plugin_configs"]["bb"]["token"] = config.plugin_configs["bb"][
            "token"
        ].get_secret_value()
        async with aiofiles.open(path, "w") as fp:
            await fp.write(ujson.dumps(config_as_dict, sort_keys=True, indent=4))

    @classmethod
    async def delete_school_authority(cls, name: str) -> None:
        cls.mkdir_p(SCHOOL_AUTHORITIES_CONFIG_PATH)
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
    async def load_school2target_mapping(
        cls, path: Path = SCHOOLS_TO_AUTHORITIES_MAPPING_PATH
    ) -> School2SchoolAuthorityMapping:
        """May raise SchoolMappingLoadingError."""
        cls.logger.debug("Loading school to authorities mapping configuration %r...", str(path))
        cls.mkdir_p(path.parent)
        if not path.exists():
            return School2SchoolAuthorityMapping(mapping={})
        try:
            async with aiofiles.open(path, "r") as fp:
                obj_dict = ujson.loads(await fp.read())
            return School2SchoolAuthorityMapping(**obj_dict)
        except (IOError, OSError, ValidationError, ValueError) as exc:
            raise SchoolMappingLoadingError(f"Loading {path.name} -> {exc}") from exc

    @classmethod
    async def save_school2target_mapping(
        cls,
        obj: School2SchoolAuthorityMapping,
        path: Path = SCHOOLS_TO_AUTHORITIES_MAPPING_PATH,
    ) -> None:
        cls.mkdir_p(path.parent)
        cls.logger.info("Writing school to school authority mapping to %s...", path)
        async with aiofiles.open(path, "w") as fp:
            await fp.write(ujson.dumps(obj.dict(), sort_keys=True, indent=4))

    @staticmethod
    def mkdir_p(path):
        try:
            path.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
