# -*- coding: utf-8 -*-

# Copyright 2024 Univention GmbH
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
import time

from utils import LOG_DIR, setup_for_sync


def check_scheduling(school_authority: str, item_name: str):
    # wait until items are scheduled.
    time.sleep(20)
    marker = "OutQueue({})".format(school_authority)
    filename = ""
    found_object = False
    with open("{}/queues.log".format(LOG_DIR)) as fp:
        lines = list(reversed(fp.readlines()))
        for i, line in enumerate(lines):
            if item_name in line:
                assert "modified" in line, line
                found_object = True
                break
        assert found_object
        for line in lines[i:]:
            if marker and "Finished handling" in line:
                filename = line.split("'", 2)[1]
                assert filename
                break

    base_path = os.path.join(
        "/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues/", school_authority
    )
    assert os.path.exists(os.path.join(base_path, "trash", filename)) is False


def test_schedule_items(schedule_item, admin_token):
    setup_for_sync("Traeger1", "DEMOSCHOOL", admin_token)
    schedule_item(item_type="user", item_name="demo_student")
    check_scheduling(school_authority="Traeger1", item_name="demo_student")

    schedule_item(item_type="group", item_name="DEMOSCHOOL-Democlass")
    check_scheduling(school_authority="Traeger1", item_name="Democlass")

    schedule_item(item_type="school", item_name="DEMOSCHOOL")
    # not explicitly scheduled users
    check_scheduling(school_authority="Traeger1", item_name="demo_teacher")
    check_scheduling(school_authority="Traeger1", item_name="demo_admin")
