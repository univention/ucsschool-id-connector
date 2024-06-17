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

import copy
import os
import random
import subprocess

from utils import LOG_DIR

LOG_LEVELS = ["DEBUG", "WARNING", "INFO", "ERROR"]


def test_logs_exist():
    for logfile in ["http.log", "queues.log"]:
        assert os.path.exists(os.path.join(LOG_DIR, logfile))


def test_log_rotation():
    def _count_gz_files():
        log_stat = {
            "http": 0,
            "queues": 0,
        }
        for file in os.listdir(LOG_DIR):
            if os.path.isfile(os.path.join(LOG_DIR, file)):
                log = file.split(".", 1)[0]
                log_stat[log] += 1 if "gz" in file else 0
        return log_stat

    num_gz_files = _count_gz_files()
    subprocess.check_call(["univention-app", "restart", "ucsschool-id-connector"])
    subprocess.check_call(["logrotate", "--force", "/etc/logrotate.conf"])
    assert _count_gz_files() == {
        "http": num_gz_files["http"] + 1,
        "queues": num_gz_files["queues"] + 1,
    }


def test_log_level():
    def _set_log_level(level):
        os.system(
            "univention-app configure ucsschool-id-connector"
            f" --set ucsschool-id-connector/log_level={level}"
        )

    def _get_log_level():
        configuration = os.popen("univention-app configure --list ucsschool-id-connector").read()
        for line in configuration.splitlines():
            if "ucsschool-id-connector/log_level" in line:
                return line.split("'", 2)[1]
        return None

    # check and get current log level
    current_log_level = _get_log_level()
    assert current_log_level is not None

    # randomly take and set new log level
    available_log_levels = copy.deepcopy(LOG_LEVELS)
    available_log_levels.remove(current_log_level)
    target_log_level = random.choice(available_log_levels)
    _set_log_level(target_log_level)
    new_log_level = _get_log_level()

    # check new log level
    assert new_log_level is not None
    assert new_log_level is not current_log_level

    # reset log level
    _set_log_level(current_log_level)
