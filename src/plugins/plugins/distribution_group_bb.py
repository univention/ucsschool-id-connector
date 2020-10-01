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

import re
from typing import Iterable, List, Pattern

from ldap3.utils.dn import parse_dn

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.queues import InQueue
from ucsschool_id_connector.user_handler import UserScheduler
from ucsschool_id_connector.utils import ConsoleAndFileLogging, school_class_dn_regex


class GroupBBDistributionImpl:
    """Distribute school classes"""

    _bb_api_regex: Pattern = None

    def __init__(self):
        self.class_dn_regex = school_class_dn_regex()
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self.user_scheduler = UserScheduler()

    @hook_impl
    async def school_authorities_to_distribute_to(
        self, obj: ListenerObject, in_queue: InQueue
    ) -> Iterable[str]:
        """
        Create list of school authorities this object should be sent to.

        All `school_authorities_to_distribute_to` hook implementations will be
        executed and the result lists will be merged. If the object type cannot
        or should not be handled by the plugin, return an empty list.

        :param ListenerObject obj: of a concrete subclass of ListenerObject
        :param InQueue in_queue: the in-queue
        :return: list of names of school authorities, they should match those
            in ``SchoolAuthorityConfiguration.name``
        :rtype: list
        """
        # The BB-API does not have a group resource, so we cannot send groups
        # to the target API - only implicitly:
        # Users can have a 'school_class' attribute. So what we do is, that we
        # trigger the (re)distribution of the groups members.
        # Only added or removed members have to be (re)sent.
        if not isinstance(obj, ListenerGroupAddModifyObject) and not isinstance(
            obj, ListenerGroupRemoveObject
        ):
            return []

        bb_school_authorities = self.bb_school_authorities(in_queue)
        if not bb_school_authorities:
            # no SchoolAuthorityConfiguration for BB-API exists
            self.logger.debug(
                "Ignoring group: no SchoolAuthorityConfiguration for BB-API found."
            )
            return []

        group_match = self.class_dn_regex.match(obj.dn)
        if not group_match:
            self.logger.debug("Ignoring non-school_class group: %r", obj)
            return []

        group_name = group_match.groupdict()["name"]
        old_users = set(obj.old_data.users if obj.old_data else [])
        if isinstance(obj, ListenerGroupAddModifyObject):
            new_users = set(obj.users)
        else:
            new_users = set()
        for dn in old_users.symmetric_difference(new_users):
            if not dn.startswith("uid="):
                self.logger.info("Ignoring non-user DN in group %r: %r", group_name, dn)
                continue
            self.logger.info("Adding member of group %r to in-queue: %r...", dn)
            user_dn_parts = parse_dn(dn)
            username = user_dn_parts[0][1]
            await self.user_scheduler.queue_user(username)
        # Always return an emtpy list, because as we cannot distribute the
        # group itself, there is never a school authority to send to.
        return []

    def bb_school_authorities(
        self, in_queue: InQueue
    ) -> List[SchoolAuthorityConfiguration]:
        return [
            out_queue.school_authority
            for out_queue in in_queue.out_queues
            if self.is_bb_api_url(out_queue.school_authority.url)
        ]

    @classmethod
    def is_bb_api_url(cls, url: str) -> bool:
        if not cls._bb_api_regex:
            cls._bb_api_regex = re.compile(r"^http.?://.+/api-bb")
        return bool(cls._bb_api_regex.match(url))


plugin_manager.register(GroupBBDistributionImpl())
