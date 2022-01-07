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

from typing import Iterable, Set

from ucsschool_id_connector.models import (
    ListenerObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.queues import InQueue
from ucsschool_id_connector.utils import ConsoleAndFileLogging


class UserDistributionImpl:
    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)

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
        s_a_names: Set[str] = set()

        if not isinstance(obj, ListenerUserAddModifyObject) and not isinstance(
            obj, ListenerUserRemoveObject
        ):
            return []

        if isinstance(obj, ListenerUserAddModifyObject):
            for school in obj.schools:
                try:
                    s_a_names.add(in_queue.school_authority_mapping[school])
                except KeyError:
                    self.logger.info(
                        "School missing in school authority mapping, ignoring: %r",
                        school,
                    )

        # add deleted school authorities, so the change/deletion will be
        # distributed by the respective out queues
        if obj.old_data:
            old_schools = obj.old_data.schools
        else:
            old_schools = []
        for school in old_schools:
            try:
                s_a_names.add(in_queue.school_authority_mapping[school])
            except KeyError:
                self.logger.info(
                    "School from 'old_data' missing in school authority" " mapping, ignoring: %r",
                    school,
                )
        return s_a_names


plugin_manager.register(UserDistributionImpl())
