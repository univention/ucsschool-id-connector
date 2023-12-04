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

import asyncio
from typing import Callable, List

from ldap3.utils.conv import escape_filter_chars

from ucsschool_id_connector.group_scheduler import GroupScheduler
from ucsschool_id_connector.ldap_access import LDAPAccess
from ucsschool_id_connector.user_scheduler import UserScheduler
from ucsschool_id_connector.utils import ConsoleAndFileLogging


async def limited_func(sem: asyncio.Semaphore, func: Callable, *args):
    async with sem:
        return await func(*args)


class SchoolScheduler:
    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self.ldap_access = LDAPAccess()
        self.user_scheduler = UserScheduler()
        self.group_scheduler = GroupScheduler()

    async def _get_school_groups(self, school: str) -> List[str]:
        filter_s = (
            f"(&(cn={escape_filter_chars(school)}-*)"
            f"(|(ucsschoolRole=school_class:school:{escape_filter_chars(school)})"
            f"(ucsschoolRole=workgroup:school:{escape_filter_chars(school)})))"
        )
        results = await self.ldap_access.search(
            filter_s=filter_s,
            attributes=["cn"],
            bind_dn=None,
            bind_pw=None,
            raise_on_bind_error=True,
        )
        return [str(group.cn) for group in results]

    async def _get_school_users(self, school: str) -> List[str]:
        filter_s = (
            f"(&(ucsschoolSchool={escape_filter_chars(school)})"
            f"(|(ucsschoolRole=teacher:school:{escape_filter_chars(school)})"
            f"(ucsschoolRole=student:school:{escape_filter_chars(school)})"
            f"(ucsschoolRole=staff:school:{escape_filter_chars(school)})"
            "))"
        )
        results = await self.ldap_access.search(
            filter_s,
            ["uid"],
            bind_dn=None,
            bind_pw=None,
            raise_on_bind_error=True,
        )
        return [str(res.uid) for res in results]

    async def queue_school(self, school: str, num_tasks: int):
        """We need to sync the users before the groups,
        because otherwise there will be missing members."""
        self.logger.info(f"Adding school to in-queue: {school}")
        usernames = await self._get_school_users(school=school)
        task_limiter = asyncio.Semaphore(num_tasks)
        tasks = [limited_func(task_limiter, self.user_scheduler.queue_user, name) for name in usernames]
        await asyncio.gather(*tasks)
        group_names = await self._get_school_groups(school=school)
        task_limiter = asyncio.Semaphore(num_tasks)
        tasks = [
            limited_func(task_limiter, self.group_scheduler.queue_group, name) for name in group_names
        ]
        await asyncio.gather(*tasks)
        self.logger.info("Done.")
