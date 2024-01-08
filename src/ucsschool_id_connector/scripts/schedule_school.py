#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright 2023 Univention GmbH
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

"""
Find users and groups of school in LDAP and add them to the in queue.
"""

import asyncio

import click

from ucsschool_id_connector.school_scheduler import SchoolScheduler
from ucsschool_id_connector.utils import ConsoleAndFileLogging


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("school")
@click.argument("num_tasks", type=click.IntRange(1, 32), default=1)
def schedule(num_tasks: int, school: str = None):
    """Schedule the distribution of a school.

    This command schedules the distribution of all school classes, work groups,
    teachers, students and staff of a school.

    school is name of the school which is to be distributed.

    num_tasks is the number of parallel tasks which is used to schedule the respective school objects.
    The value is allowed to be in the range of 1 to 32. The default value is 1.

    Example:

        # Schedule the distribution of DEMOSCHOOL with 2 tasks
        schedule_school DEMOSCHOOL 2
    """
    scheduler = SchoolScheduler()
    ConsoleAndFileLogging.add_console_handler(scheduler.user_scheduler.logger)
    ConsoleAndFileLogging.add_console_handler(scheduler.group_scheduler.logger)
    ConsoleAndFileLogging.add_console_handler(scheduler.logger)
    asyncio.run(scheduler.queue_school(school=school, num_tasks=num_tasks))
    scheduler.logger.debug("Done.")


if __name__ == "__main__":
    schedule()
