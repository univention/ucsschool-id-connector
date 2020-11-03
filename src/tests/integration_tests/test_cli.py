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

import subprocess

import pytest

from ucsschool_id_connector.config_storage import ConfigurationStorage
from ucsschool_id_connector.constants import SCHOOL_AUTHORITIES_CONFIG_PATH
from ucsschool_id_connector.models import SchoolAuthorityConfiguration


@pytest.mark.asyncio
async def test_migrate_school_authority_configuration_to_plugins_ok(
    temp_clear_dir, bb_school_authority_configuration
):
    temp_clear_dir(SCHOOL_AUTHORITIES_CONFIG_PATH)
    sac: SchoolAuthorityConfiguration = bb_school_authority_configuration()
    path = SCHOOL_AUTHORITIES_CONFIG_PATH / f"{sac.name}.json"
    try:
        await ConfigurationStorage.save_school_authority(sac, path)
        process = subprocess.Popen(
            ["python3", "-m", "ucsschool_id_connector", "migrate-school-authority-configurations"],
            stdout=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        stdout = stdout.decode()
        assert process.returncode == 0
        assert "Starting migration" in stdout
        assert "End of migration" in stdout
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


@pytest.mark.asyncio
async def test_migrate_school_authority_configuration_to_plugins_error(temp_clear_dir, faker_obj):
    temp_clear_dir(SCHOOL_AUTHORITIES_CONFIG_PATH)
    with open(SCHOOL_AUTHORITIES_CONFIG_PATH / faker_obj.file_name(extension="json"), "w") as fp:
        fp.write("{}")
    process = subprocess.Popen(
        ["python3", "-m", "ucsschool_id_connector", "migrate-school-authority-configurations"],
        stdout=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    stdout = stdout.decode()
    assert process.returncode == 1
    assert "Unknown configuration" in stdout or "Missing 'url'" in stdout
