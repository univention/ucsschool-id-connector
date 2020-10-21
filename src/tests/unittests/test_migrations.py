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

import json
import logging
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from ucsschool_id_connector.config_storage import ConfigurationStorage
from ucsschool_id_connector.migrations import logger, migrate_school_authority_configuration_to_plugins
from ucsschool_id_connector.models import SchoolAuthorityConfiguration


@pytest.mark.asyncio
async def test_migrate_school_authority_configuration_to_plugins(
    school_authority_configuration, temp_file_func
):
    logger.addHandler(logging.StreamHandler(stream=sys.stdout))
    logger.setLevel(logging.DEBUG)
    expected: SchoolAuthorityConfiguration = school_authority_configuration()
    old_config = expected.dict()
    old_config["password"] = old_config["plugin_configs"]["bb"].pop("token").get_secret_value()
    old_config["passwords_target_attribute"] = old_config["plugin_configs"]["bb"].pop(
        "passwords_target_attribute"
    )
    del old_config["plugin_configs"]
    old_config["postprocessing_plugins"] = ["default"]

    ori_path: Path = temp_file_func(suffix=".json")
    # old_config["name"] = ori_path.stem
    with open(ori_path, "w") as fp:
        json.dump(
            old_config,
            fp,
            sort_keys=True,
            indent=4,
        )

    backup_path = ori_path.with_suffix(".json.bak")
    try:
        with pytest.raises(ValidationError):
            await ConfigurationStorage.load_school_authority(ori_path)

        await migrate_school_authority_configuration_to_plugins([ori_path])

        assert backup_path.exists()
        with open(backup_path) as fp:
            backup_config = json.load(fp)
        assert backup_config == old_config
    finally:
        try:
            backup_path.unlink()
        except FileNotFoundError:
            pass

    assert ori_path.exists()
    with open(ori_path) as fp:
        new_config = json.load(fp)
    expected.plugins = ["bb"]
    expected.plugin_configs["bb"]["token"] = expected.plugin_configs["bb"]["token"].get_secret_value()
    assert new_config == expected.dict()
