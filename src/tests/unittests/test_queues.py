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

import os
from unittest.mock import Mock, patch

import pytest

import ucsschool_id_connector.constants
import ucsschool_id_connector.db
import ucsschool_id_connector.models
import ucsschool_id_connector.queues


@pytest.mark.asyncio
async def test_load_listener_file_example_user(example_user_json_path_real, temp_dir_func):
    in_queue = ucsschool_id_connector.queues.InQueue(path=temp_dir_func())
    obj = await in_queue.load_listener_file(example_user_json_path_real)
    assert isinstance(obj, ucsschool_id_connector.models.ListenerUserAddModifyObject)


@pytest.mark.asyncio
async def test_load_listener_file_example_user_remove(example_user_remove_json_path_real, temp_dir_func):
    in_queue = ucsschool_id_connector.queues.InQueue(path=temp_dir_func())
    obj = await in_queue.load_listener_file(example_user_remove_json_path_real)
    assert isinstance(obj, ucsschool_id_connector.models.ListenerUserRemoveObject)


@pytest.mark.asyncio
async def test_preprocess_add_mod_file(mock_plugins, example_user_json_path_copy, temp_dir_func):
    mock_plugin_impls, db_path = mock_plugins
    temp_dir = temp_dir_func()
    add_mod_json_path = example_user_json_path_copy(temp_dir)
    in_queue = ucsschool_id_connector.queues.InQueue(path=temp_dir)

    add_mod_obj = await in_queue.load_listener_file(add_mod_json_path)
    assert isinstance(add_mod_obj, ucsschool_id_connector.models.ListenerUserAddModifyObject)
    assert add_mod_obj.user_passwords is None  # not yet preprocessed

    new_path = await in_queue.preprocess_file(add_mod_json_path)
    assert new_path.name == f"{add_mod_json_path.name[:-5]}_ready.json"

    add_mod_obj_new = await in_queue.load_listener_file(new_path)
    assert isinstance(add_mod_obj_new, ucsschool_id_connector.models.ListenerUserAddModifyObject)
    assert add_mod_obj_new.id == add_mod_obj.id
    assert isinstance(add_mod_obj_new.user_passwords, ucsschool_id_connector.models.UserPasswords)

    old_data_db = ucsschool_id_connector.db.OldDataDB(
        db_path, ucsschool_id_connector.models.ListenerUserOldDataEntry
    )
    assert add_mod_obj.id in old_data_db
    del old_data_db[add_mod_obj.id]


@pytest.mark.asyncio
async def test_preprocess_del_file(mock_plugins, example_user_remove_json_path_copy, temp_dir_func):
    mock_plugin_impls, db_path = mock_plugins

    temp_dir = temp_dir_func()
    del_json_path = example_user_remove_json_path_copy(temp_dir)
    in_queue = ucsschool_id_connector.queues.InQueue(path=temp_dir)

    del_obj = await in_queue.load_listener_file(del_json_path)
    assert isinstance(del_obj, ucsschool_id_connector.models.ListenerUserRemoveObject)

    old_data_db = ucsschool_id_connector.db.OldDataDB(
        db_path, ucsschool_id_connector.models.ListenerUserOldDataEntry
    )
    assert del_obj.id not in old_data_db

    new_path = await in_queue.preprocess_file(del_json_path)
    assert new_path.name == f"{del_json_path.name[:-5]}_ready.json"

    del_obj_new = await in_queue.load_listener_file(new_path)
    assert isinstance(del_obj_new, ucsschool_id_connector.models.ListenerUserRemoveObject)
    assert del_obj_new.old_data is None


@pytest.mark.asyncio
async def test_preprocess_del_file_with_old_data(
    mock_plugins,
    example_user_json_path_copy,
    example_user_remove_json_path_copy,
    temp_dir_func,
):
    mock_plugin_impls, db_path = mock_plugins
    temp_dir = temp_dir_func()
    add_mod_json_path = example_user_json_path_copy(temp_dir)
    del_json_path = example_user_remove_json_path_copy(temp_dir)
    in_queue = ucsschool_id_connector.queues.InQueue(path=temp_dir)

    # preprocess add/mod file to get IDs into old_db
    add_mod_obj = await in_queue.load_listener_file(add_mod_json_path)
    assert isinstance(add_mod_obj, ucsschool_id_connector.models.ListenerUserAddModifyObject)
    await in_queue.preprocess_file(add_mod_json_path)
    old_data_db = ucsschool_id_connector.db.OldDataDB(
        db_path, ucsschool_id_connector.models.ListenerUserOldDataEntry
    )
    assert add_mod_obj.id in old_data_db

    # preprocessed del file should get old_data from db
    del_obj = await in_queue.load_listener_file(del_json_path)
    assert del_obj.id == add_mod_obj.id
    assert isinstance(del_obj, ucsschool_id_connector.models.ListenerUserRemoveObject)
    new_path = await in_queue.preprocess_file(del_json_path)
    del_obj_new = await in_queue.load_listener_file(new_path)

    assert isinstance(del_obj_new, ucsschool_id_connector.models.ListenerUserRemoveObject)
    assert del_obj_new.id == add_mod_obj.id
    assert del_obj_new.old_data is not None
    assert del_obj_new.old_data.record_uid == add_mod_obj.record_uid
    assert del_obj_new.old_data.source_uid == add_mod_obj.source_uid
    assert del_obj_new.old_data.schools == add_mod_obj.schools


@pytest.mark.asyncio
async def test_handle_move_files_to_trash_dir_when_server_error_are_raised(
    example_user_json_path_copy,
    temp_dir_func,
    school_authority_configuration,
):
    temp_dir = temp_dir_func()
    add_mod_json_path = example_user_json_path_copy(temp_dir)
    out_queue = ucsschool_id_connector.queues.OutQueue(
        name="test",
        path=temp_dir,
        school_authority=school_authority_configuration(),
    )
    exception = ValueError()

    def fake_filter_plugins(*args, **kwargs):
        raise exception

    out_queue.logger.exception = Mock()

    with patch("ucsschool_id_connector.queues.filter_plugins", fake_filter_plugins):
        await out_queue.handle(add_mod_json_path)
        assert os.path.exists(os.path.join(out_queue.trash_dir, os.path.basename(add_mod_json_path)))
        assert not os.path.exists(add_mod_json_path)
        out_queue.logger.exception.assert_called_with(exception)


@pytest.mark.asyncio
async def test_handle_move_files_to_trash_dir_after_listener_loading_error(
    example_user_json_path_copy,
    temp_dir_func,
    school_authority_configuration,
):
    temp_dir = temp_dir_func()
    add_mod_json_path = example_user_json_path_copy(temp_dir)
    out_queue = ucsschool_id_connector.queues.OutQueue(
        name="test",
        path=temp_dir,
        school_authority=school_authority_configuration(),
    )

    def fake_load_listener_file(*args, **kwargs):
        raise ucsschool_id_connector.queues.ListenerLoadingError()

    out_queue.logger.error = Mock()
    out_queue.load_listener_file = fake_load_listener_file
    await out_queue.handle(add_mod_json_path)
    assert os.path.exists(os.path.join(out_queue.trash_dir, os.path.basename(add_mod_json_path)))
    assert not os.path.exists(add_mod_json_path)
    out_queue.logger.error.assert_called_with(
        "Error loading or invalid listener file %r.", add_mod_json_path.name
    )
