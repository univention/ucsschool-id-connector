# -*- coding: utf-8 -*-

# Copyright 2020 Univention GmbH
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
import pprint
import shutil
from pathlib import Path
from typing import Any, Dict, List

import ujson
from pydantic import ValidationError

from .config_storage import ConfigurationStorage
from .models import SchoolAuthorityConfiguration

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    ...


def _die(msg: str, exc: Exception = None) -> None:
    logger.error(msg)
    if exc:
        raise ConversionError(msg) from exc
    else:
        raise ConversionError(msg)


def _read_school_auth_config(path: Path) -> Dict[str, Any]:
    """
    :raises ConversionError: if the file could not be loaded
    """
    with open(path, "r") as fp:
        try:
            return ujson.load(fp)
        except ValueError as exc:
            _die(f"Bad JSON file: {exc!s}", exc)
        except EnvironmentError as exc:
            _die(f"Error reading file: {exc!s}", exc)


async def _test_load_as_school_authority_configuration(path: Path) -> SchoolAuthorityConfiguration:
    """
    :raises ConversionError: if the file could not be read as `SchoolAuthorityConfiguration`
    """
    try:
        school_authority = await ConfigurationStorage.load_school_authority(path)
        logger.info("    Successfully loaded school authority configuration.")
        return school_authority
    except (IOError, OSError, ValueError, ValidationError) as exc:
        _die(f"Error loading configuration file '{path!s}': {exc!s}", exc)


async def migrate_school_authority_configuration_to_plugins(paths: List[Path] = None) -> None:
    """
    Convert all SchoolAuthorityConfiguration JSON files to use the
    "plugin_configs" nested dict.

    :raises ConversionError: if a file could not be loaded or converted
    """
    logger.info("==> Starting migration of 'SchoolAuthorityConfiguration' to use 'plugin_configs'. <==")
    for path in paths or ConfigurationStorage.school_authority_config_files():
        logger.info("Checking if migration is required for %r...", str(path))
        obj = _read_school_auth_config(path)
        if "plugin_configs" in obj and "mapping" not in obj:
            logger.info(
                "    Has 'plugin_configs' and not 'mapping', trying to load as "
                "'SchoolAuthorityConfiguration'..."
            )
            await _test_load_as_school_authority_configuration(path)
            logger.info("    No migration necessary.")
            continue
        else:
            logger.info("    No 'plugin_configs' found or 'mapping' found, converting...")
            logger.info("    Original JSON:\n%s", pprint.pformat(obj))
            if "url" not in obj:
                _die("Missing 'url' in JSON object.")
            if "api-bb" in obj["url"]:
                logger.info("    Detected a configuration for the BB-API.")
                for attr in ("mapping", "password", "passwords_target_attribute"):
                    if attr not in obj:
                        _die(f"Missing {attr!r} in JSON object.")
                obj["plugin_configs"] = {
                    "bb": {
                        "mapping": {
                            "users": obj.pop("mapping"),
                            "school_classes": {
                                "name": "name",
                                "description": "description",
                                "school": "school",
                                "users": "users",
                            },
                        },
                        "token": obj.pop("password"),
                        "passwords_target_attribute": obj.pop("passwords_target_attribute"),
                    },
                }
                obj.pop("postprocessing_plugins", None)  # deprecated
                obj["plugins"] = ["bb"]
                logger.info("    New JSON:\n%s", pprint.pformat(obj))

                backup_path = path.with_suffix(".json.bak")
                shutil.copy2(path, backup_path)
                logger.info("Created backup %r.", str(backup_path))

                sac = SchoolAuthorityConfiguration.parse_obj(obj)
                await ConfigurationStorage.save_school_authority(sac, path)
                logger.info("New 'SchoolAuthorityConfiguration' was written, testing it now...")
                await _test_load_as_school_authority_configuration(path)
                logger.info("Successfully migrated %r to use 'plugin_configs' nested dict.", path.name)
            else:
                _die(
                    f"    Unknown configuration, cannot migrate. JSON object:\n{'-' * 80}\n"
                    f"{pprint.pformat(obj)}\n{'-' * 80}"
                )
    logger.info("==> End of migration of 'SchoolAuthorityConfiguration' to use 'plugin_configs'. <==")
