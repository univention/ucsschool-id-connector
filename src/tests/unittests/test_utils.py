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

import time
from unittest.mock import patch

import pytest
from faker import Faker

import id_sync.utils

fake = Faker()


@pytest.fixture
async def reopen_cache():
    """reopen the ucrv cache that was closed by test_get_token_ttl()"""
    yield
    try:
        id_sync.utils._get_ucrv_cached.open()
    except RuntimeError:
        pass


@pytest.mark.asyncio
async def test_get_ucrv_unknown_key_no_default(temp_file_func):
    ucr_file = temp_file_func()
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file):
        value = await id_sync.utils.get_ucrv(fake.pystr())
    assert value is None


@pytest.mark.asyncio
async def test_get_ucrv_unknown_key_with_default(temp_file_func):
    ucr_file = temp_file_func()
    exp_val = fake.pystr()
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file):
        value = await id_sync.utils.get_ucrv(fake.pystr(), exp_val)
    assert value is exp_val


@pytest.mark.asyncio
async def test_get_ucrv_known_key(temp_file_func):
    ucr_file = temp_file_func()
    key, exp_val = fake.pystr(), fake.pystr()
    with open(ucr_file, "w") as fp:
        fp.write(f"{key}: {exp_val}")
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file):
        value = await id_sync.utils.get_ucrv(key)
    assert value == exp_val


@pytest.mark.asyncio
async def test_get_ucrv_stale_cache(temp_file_func):
    ucr_file = temp_file_func()
    key, exp_val1, exp_val2 = fake.pystr(), fake.pystr(), fake.pystr()
    with open(ucr_file, "w") as fp:
        fp.write(f"{key}: {exp_val1}")
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file):
        value = await id_sync.utils.get_ucrv(key)
        assert value == exp_val1
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val2}")
        value = await id_sync.utils.get_ucrv(key)
        assert value == exp_val2


@pytest.mark.asyncio
async def test_get_ucrv_cache_close(temp_file_func, reopen_cache):
    ucr_file = temp_file_func()
    key, exp_val = fake.pystr(), fake.pystr()
    with open(ucr_file, "w") as fp:
        fp.write(f"{key}: {exp_val}")
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file):
        value = await id_sync.utils.get_ucrv(key)
        assert value == exp_val
        await id_sync.utils.close_ucr_cache()
        with pytest.raises(RuntimeError):
            await id_sync.utils.get_ucrv(key)
        with pytest.raises(RuntimeError):
            await id_sync.utils.close_ucr_cache()


@pytest.mark.asyncio
async def test_get_token_ttl(temp_file_func):
    ucr_file = temp_file_func()
    key, default, exp_val = fake.pystr(), str(fake.pyint()), str(fake.pyint())
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file), patch(
        "id_sync.utils.UCRV_TOKEN_TTL", (key, default)
    ):
        value = await id_sync.utils.get_token_ttl()
        assert value == int(default)
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val}")
        value = await id_sync.utils.get_token_ttl()
        assert value == int(exp_val)


@pytest.mark.asyncio
async def test_get_source_uid(temp_file_func):
    ucr_file = temp_file_func()
    key, default, exp_val = fake.pystr(), fake.pystr(), fake.pystr()
    with patch("id_sync.utils.UCR_DB_FILE", ucr_file), patch(
        "id_sync.utils.UCRV_SOURCE_UID", (key, default)
    ):
        value = await id_sync.utils.get_source_uid()
        assert value == default
        time.sleep(0.01)
        with open(ucr_file, "w") as fp:
            fp.write(f"{key}: {exp_val}")
        value = await id_sync.utils.get_source_uid()
        assert value == exp_val
