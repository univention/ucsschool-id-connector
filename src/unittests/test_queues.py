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

import tempfile
from pathlib import Path

import pytest

import id_sync.constants
import id_sync.db
import id_sync.models
import id_sync.queues


@pytest.mark.asyncio
async def test_load_listener_file_example_user(monkeypatch, mock_plugins, example_user_json_path_real):
    with tempfile.TemporaryDirectory() as temp_dir:
        in_queue = id_sync.queues.InQueue(path=Path(temp_dir))
    obj = await in_queue.load_listener_file(example_user_json_path_real)
    assert isinstance(obj, id_sync.models.ListenerUserAddModifyObject)


@pytest.mark.asyncio
async def test_load_listener_file_example_user_remove(monkeypatch, mock_plugins, example_user_remove_json_path_real):
    with tempfile.TemporaryDirectory() as temp_dir:
        in_queue = id_sync.queues.InQueue(path=Path(temp_dir))
    obj = await in_queue.load_listener_file(example_user_remove_json_path_real)
    assert isinstance(obj, id_sync.models.ListenerUserRemoveObject)


@pytest.mark.asyncio
async def test_preprocess_add_mod_file(mock_plugins, example_user_json_path_copy):
    mock_plugin_impls, db_path, fake_user_passwords_object = mock_plugins
    with tempfile.TemporaryDirectory() as temp_dir:
        add_mod_json_path = example_user_json_path_copy(temp_dir)
        in_queue = id_sync.queues.InQueue(path=Path(temp_dir))

        add_mod_obj = await in_queue.load_listener_file(add_mod_json_path)
        assert isinstance(add_mod_obj, id_sync.models.ListenerUserAddModifyObject)
        assert add_mod_obj.user_passwords is None  # not yet preprocessed

        new_path = await in_queue.preprocess_file(add_mod_json_path)
        assert new_path.name == f"{add_mod_json_path.name[:-5]}_ready.json"

        add_mod_obj_new = await in_queue.load_listener_file(new_path)

    assert isinstance(add_mod_obj_new, id_sync.models.ListenerUserAddModifyObject)
    assert add_mod_obj_new.id == add_mod_obj.id
    assert isinstance(add_mod_obj_new.user_passwords, id_sync.models.UserPasswords)

    old_data_db = id_sync.db.OldDataDB(db_path, id_sync.models.ListenerUserOldDataEntry)
    assert add_mod_obj.id in old_data_db
    del old_data_db[add_mod_obj.id]


@pytest.mark.asyncio
async def test_preprocess_del_file(mock_plugins, example_user_remove_json_path_copy):
    mock_plugin_impls, db_path, fake_user_passwords_object = mock_plugins

    with tempfile.TemporaryDirectory() as temp_dir:
        del_json_path = example_user_remove_json_path_copy(temp_dir)
        in_queue = id_sync.queues.InQueue(path=Path(temp_dir))

        del_obj = await in_queue.load_listener_file(del_json_path)
        assert isinstance(del_obj, id_sync.models.ListenerUserRemoveObject)

        old_data_db = id_sync.db.OldDataDB(db_path, id_sync.models.ListenerUserOldDataEntry)
        assert del_obj.id not in old_data_db

        new_path = await in_queue.preprocess_file(del_json_path)
        assert new_path.name == f"{del_json_path.name[:-5]}_ready.json"
        del_obj_new = await in_queue.load_listener_file(new_path)

    assert isinstance(del_obj_new, id_sync.models.ListenerUserRemoveObject)
    assert del_obj_new.old_data is None


@pytest.mark.asyncio
async def test_preprocess_del_file_with_old_data(mock_plugins, example_user_json_path_copy, example_user_remove_json_path_copy):
    mock_plugin_impls, db_path, fake_user_passwords_object = mock_plugins
    with tempfile.TemporaryDirectory() as temp_dir:
        add_mod_json_path = example_user_json_path_copy(temp_dir)
        del_json_path = example_user_remove_json_path_copy(temp_dir)
        in_queue = id_sync.queues.InQueue(path=Path(temp_dir))

        # preprocess add/mod file to get IDs into old_db
        add_mod_obj = await in_queue.load_listener_file(add_mod_json_path)
        assert isinstance(add_mod_obj, id_sync.models.ListenerUserAddModifyObject)
        new_path = await in_queue.preprocess_file(add_mod_json_path)
        old_data_db = id_sync.db.OldDataDB(db_path, id_sync.models.ListenerUserOldDataEntry)
        assert add_mod_obj.id in old_data_db

        # preprocessed del file should get old_data from db
        del_obj = await in_queue.load_listener_file(del_json_path)
        assert del_obj.id == add_mod_obj.id
        assert isinstance(del_obj, id_sync.models.ListenerUserRemoveObject)
        new_path = await in_queue.preprocess_file(del_json_path)
        del_obj_new = await in_queue.load_listener_file(new_path)

    assert isinstance(del_obj_new, id_sync.models.ListenerUserRemoveObject)
    assert del_obj_new.id == add_mod_obj.id
    assert del_obj_new.old_data is not None
    assert del_obj_new.old_data.record_uid == add_mod_obj.object.get("record_uid")
    assert del_obj_new.old_data.source_uid == add_mod_obj.object.get("source_uid")
    assert del_obj_new.old_data.schools == add_mod_obj.object.get("school")

# TODO: test UserHandler
# TODO: test MvDstEntry
