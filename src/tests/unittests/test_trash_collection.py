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

import os
import random
import time
from datetime import datetime, timedelta

import pytest

from ucsschool_id_connector.scripts.listener_trash_cleaner import delete_up_from_day


@pytest.mark.skipif(not os.path.exists("/.dockerenv"), reason="Not run in docker container")
def test_cleanup_script_executeable():
    assert os.access("/ucsschool-id-connector/src/listener_trash_cleaner.py", os.X_OK)


def test_cleanup(tmpdir_factory):
    tmp_trash_path = tmpdir_factory.mktemp("trash")
    random_days = [random.randint(0, 100) for _ in range(20)]
    offset = random_days[random.randint(0, 19)]
    files = []
    for i, r_int in enumerate(random_days):
        filename = f"{i}_{r_int}.txt"
        if r_int < offset:
            files.append(filename)

        tmp_trash_path.join(filename).write_text("dummy_content", encoding="UTF-8")
        access_time = time.mktime(datetime.now().timetuple())
        modification_time = time.mktime((datetime.now() - timedelta(days=r_int)).timetuple())

        os.utime(tmp_trash_path.join(filename), (access_time, modification_time))

    delete_up_from_day(offset=offset, trash_path=tmp_trash_path)

    assert set(files) == set(os.listdir(tmp_trash_path))
