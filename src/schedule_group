#!/usr/bin/python3
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

"""
Find groups in LDAP and add them to the in queue.
"""

import asyncio

import click

from ucsschool_id_connector.group_scheduler import GroupScheduler
from ucsschool_id_connector.utils import ConsoleAndFileLogging


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("groupname")
def schedule(groupname: str = None):
    """Schedule the distribution of a group.

    This command schedules the distribution of a group.

    groupname is the name of the group which is to be distributed.

    Example:

        # Schedule the distribution of class DEMOSCHOOL-democlass
        schedule_group DEMOSCHOOL-democlass
    """
    scheduler = GroupScheduler()
    ConsoleAndFileLogging.add_console_handler(scheduler.logger)
    asyncio.run(scheduler.queue_group(groupname))
    scheduler.logger.debug("Done.")


if __name__ == "__main__":
    schedule()
