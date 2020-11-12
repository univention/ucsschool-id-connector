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

import json
import os
from unittest.mock import patch

import faker
import pytest

import ucsschool_id_connector.config_storage
import ucsschool_id_connector.models

fake = faker.Faker()


@pytest.mark.asyncio
async def test_load_school_authorities_empty(temp_dir_func):
    """handle no configs exist"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        async for read_sac in cs.load_school_authorities():
            assert False, f"Should be empty, but got: {read_sac!r}"  # pragma: no cover


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ("kelvin",))
async def test_load_school_authorities(api, temp_dir_func, kelvin_school_authority_configuration):
    """open a config"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    sac = {
        "kelvin": kelvin_school_authority_configuration(),
    }[api]
    password = {
        "kelvin": "password",
    }[api]
    sac_dict = sac.dict()
    sac_dict["plugin_configs"][api][password] = sac.plugin_configs[api][password].get_secret_value()
    with open(sac_dir / f"{sac.name}.json", "w") as fp:
        json.dump(sac_dict, fp)
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        async for read_sac in cs.load_school_authorities():
            read_sac_dict = read_sac.dict()
            read_sac_dict["plugin_configs"][api][password] = read_sac.plugin_configs[api][
                password
            ].get_secret_value()
            assert sac_dict == read_sac_dict


@pytest.mark.asyncio
async def test_delete_school_authority_non_existent(temp_dir_func):
    """handle missing file"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        await cs.delete_school_authority(fake.user_name())


@pytest.mark.asyncio
async def test_delete_school_authority_not_a_file(temp_dir_func):
    """handle directory instead of file"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        name = fake.user_name()
        os.mkdir(sac_dir / f"{name}.json")
        await cs.delete_school_authority(name)


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ("kelvin",))
async def test_delete_school_authority(api, temp_dir_func, kelvin_school_authority_configuration):
    """handle real school_authority"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    sac = {
        "kelvin": kelvin_school_authority_configuration(),
    }[api]
    password = {
        "kelvin": "password",
    }[api]
    sac_dict = sac.dict()
    sac_dict["plugin_configs"][api][password] = sac.plugin_configs[api][password].get_secret_value()
    with open(sac_dir / f"{sac.name}.json", "w") as fp:
        json.dump(sac_dict, fp)
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        await cs.delete_school_authority(sac.name)


@pytest.mark.asyncio
@pytest.mark.parametrize("api", ("kelvin",))
async def test_save_school_authorities(api, temp_dir_func, kelvin_school_authority_configuration):
    """handle real school_authority"""
    log_dir = temp_dir_func()
    sac_dir = temp_dir_func()
    sac1, sac2 = {
        "kelvin": (kelvin_school_authority_configuration(), kelvin_school_authority_configuration()),
    }[api]
    password = {
        "kelvin": "password",
    }[api]
    sac1_dict = sac1.dict()
    sac1_dict["plugin_configs"][api][password] = sac1.plugin_configs[api][password].get_secret_value()
    sac2_dict = sac2.dict()
    sac2_dict["plugin_configs"][api][password] = sac2.plugin_configs[api][password].get_secret_value()
    with patch("ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH", sac_dir), patch(
        "ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir
    ):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        await cs.save_school_authorities([sac1, sac2])
    with open(sac_dir / f"{sac1.name}.json", "r") as fp:
        sac1_load_dict = json.load(fp)
    assert sac1_dict == sac1_load_dict
    with open(sac_dir / f"{sac2.name}.json", "r") as fp:
        sac2_load_dict = json.load(fp)
    assert sac2_dict == sac2_load_dict


@pytest.mark.asyncio
async def test_load_school2target_mapping(temp_dir_func):
    """test loading a School2SchoolAuthorityMapping"""
    log_dir = temp_dir_func()
    s2sam_dir = temp_dir_func()
    s2sam_file = s2sam_dir / fake.file_name()
    s2sam_dict = {"mapping": fake.pydict(100, True, str)}
    with open(s2sam_file, "w") as fp:
        json.dump(s2sam_dict, fp)
    with patch(
        "ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH",
        s2sam_dir,
    ), patch("ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        s2sam = await cs.load_school2target_mapping(s2sam_file)
    assert s2sam.dict() == s2sam_dict


@pytest.mark.asyncio
async def test_save_school2target_mapping(temp_dir_func):
    """test saving School2SchoolAuthorityMapping"""
    log_dir = temp_dir_func()
    s2sam_dir = temp_dir_func()
    s2sam_file = s2sam_dir / fake.file_name()
    s2sam = ucsschool_id_connector.models.School2SchoolAuthorityMapping(
        mapping=fake.pydict(100, True, str)
    )
    with patch(
        "ucsschool_id_connector.config_storage.SCHOOL_AUTHORITIES_CONFIG_PATH",
        s2sam_dir,
    ), patch("ucsschool_id_connector.config_storage.LOG_FILE_PATH_QUEUES", log_dir):
        cs = ucsschool_id_connector.config_storage.ConfigurationStorage()
        await cs.save_school2target_mapping(s2sam, s2sam_file)
    with open(s2sam_file, "r") as fp:
        s2sam_load_dict = json.load(fp)
    assert s2sam.dict() == s2sam_load_dict
