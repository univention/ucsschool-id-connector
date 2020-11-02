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

from typing import Iterable, Union, cast

from ldap3.utils.dn import parse_dn

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
)
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.queues import InQueue
from ucsschool_id_connector.user_scheduler import UserScheduler
from ucsschool_id_connector_defaults.distribution_group_base import GroupDistributionImplBase


class BBGroupDistribution(GroupDistributionImplBase):
    """Distribute school classes"""

    plugin_name = "bb"
    target_api_name = "BB-API"
    _user_scheduler: UserScheduler = None

    @property
    def user_scheduler(self):
        # Made this a property, so that if BB-API is not used, no UserScheduler
        # object is ever created.
        if not self._user_scheduler:
            self.__class__._user_scheduler = UserScheduler()
        return self._user_scheduler

    @hook_impl
    async def school_authorities_to_distribute_to(
        self, obj: ListenerObject, in_queue: InQueue
    ) -> Iterable[str]:
        # The BB-API does not have a group resource, so we cannot send groups
        # to the target API - only implicitly:
        # Users can have a 'school_class' attribute. So what we do is, that we
        # trigger the (re)distribution of the groups members.
        # Only added or removed members have to be (re)sent.
        res = await super(BBGroupDistribution, self).school_authorities_to_distribute_to(obj, in_queue)
        if not res:
            return []
        # else ignore, see comment above
        obj = cast(Union[ListenerGroupAddModifyObject, ListenerGroupRemoveObject], obj)
        old_users = set(obj.old_data.users if obj.old_data else [])
        if isinstance(obj, ListenerGroupAddModifyObject):
            new_users = set(obj.users)
        else:
            new_users = set()
        group_match = self.class_dn_regex.match(obj.dn)
        group_name = group_match.groupdict()["name"]
        for dn in old_users.symmetric_difference(new_users):
            if not dn.startswith("uid="):
                self.logger.info("Ignoring non-user DN in group %r: %r", group_name, dn)
                continue
            self.logger.info("Adding member of group %r to in-queue: %r...", group_name, dn)
            user_dn_parts = parse_dn(dn)
            username = user_dn_parts[0][1]
            await self.user_scheduler.queue_user(username)
        # Always return an emtpy list, because as we cannot distribute the
        # group itself, there is never a school authority to send to.
        return []


plugin_manager.register(BBGroupDistribution())
