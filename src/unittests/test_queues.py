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

from pathlib import Path
from unittest.mock import patch

import pytest

import id_sync.models
import id_sync.queues


@pytest.mark.asyncio
async def test_load_listener_file_example_user(monkeypatch, mock_plugins):
    monkeypatch.setenv("ldap_base", "dc=foo,dc=bar")
    monkeypatch.setenv("ldap_server_name", "localhost")
    monkeypatch.setenv("ldap_server_port", "7389")
    with patch("id_sync.db.OldDataDB"), patch.object(Path, "mkdir"):
        inqueue = id_sync.queues.InQueue()
        obj = await inqueue.load_listener_file(
            Path(__file__).parent.parent / "example_user.json"
        )
    assert isinstance(obj, id_sync.models.ListenerUserAddModifyObject)


@pytest.mark.asyncio
async def test_load_listener_file_example_user_remove(monkeypatch, mock_plugins):
    monkeypatch.setenv("ldap_base", "dc=foo,dc=bar")
    monkeypatch.setenv("ldap_server_name", "localhost")
    monkeypatch.setenv("ldap_server_port", "7389")
    with patch("id_sync.db.OldDataDB"), patch.object(Path, "mkdir"):
        inqueue = id_sync.queues.InQueue()
    obj = await inqueue.load_listener_file(
        Path(__file__).parent.parent / "example_user_remove.json"
    )
    assert isinstance(obj, id_sync.models.ListenerRemoveObject)


# TODO: test UserHandler
# TODO: test MvDstEntry
