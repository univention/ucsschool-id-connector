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

import datetime
import importlib
import json
import os
from pathlib import Path
from typing import Iterator, cast
from unittest.mock import patch

from click.testing import CliRunner


def test_schedule_group(temp_dir_func, ldap_access_mock):
    fake_group_object = ldap_access_mock._group
    appcenter_listener_path = temp_dir_func()

    module_name = "schedule_group"
    path = Path(__file__).parent.parent.parent / module_name
    assert path.exists()
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)

    with patch("ucsschool_id_connector.group_scheduler.LDAPAccess", ldap_access_mock), patch(
        "ucsschool_id_connector.group_scheduler.APPCENTER_LISTENER_PATH",
        appcenter_listener_path,
    ):
        spec.loader.exec_module(module)
        schedule = getattr(module, "schedule")
        runner = CliRunner()
        result = runner.invoke(schedule, [fake_group_object.groupname])
    assert result.exit_code == 0

    print("Fake APPCENTER_LISTENER_PATH contents:")
    with cast(Iterator[os.DirEntry], os.scandir(appcenter_listener_path)) as dir_entries:
        for entry in dir_entries:
            print(entry.path)
            assert entry.name.startswith(datetime.datetime.now().strftime("%Y-%m-%d"))
            assert entry.name.endswith(".json")
            with open(entry, "r") as fp:
                obj = json.load(fp)
            assert obj["entry_uuid"] == fake_group_object.attributes["entryUUID"][0]
            assert obj["dn"] == fake_group_object.dn
            assert obj["object_type"] == "groups/group"
            assert obj["command"] == "m"
