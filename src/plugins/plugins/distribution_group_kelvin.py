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

from typing import Iterable, List

from ucsschool_id_connector.models import ListenerObject, SchoolAuthorityConfiguration
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.queues import InQueue, OutQueue
from ucsschool_id_connector_defaults.distribution_group_base import GroupDistributionImplBase


class KelvinGroupDistribution(GroupDistributionImplBase):
    """Distribute school classes to Kelvin API"""

    plugin_name = "kelvin"
    target_api_name = "Kelvin API"

    @staticmethod
    def _get_school_authority_configs(out_queues: List[OutQueue]) -> List[SchoolAuthorityConfiguration]:
        return [
            out_queue.school_authority
            for out_queue in out_queues
            if "kelvin" in out_queue.school_authority.plugins and out_queue.school_authority.active
        ]

    @hook_impl
    async def school_authorities_to_distribute_to(
        self, obj: ListenerObject, in_queue: InQueue
    ) -> Iterable[str]:
        kelvin_s_a = self._get_school_authority_configs(in_queue.out_queues)
        if not kelvin_s_a:
            self.logger.debug("No active Kelvin configuration found.")
            return []
        return await super().school_authorities_to_distribute_to(obj, in_queue)


plugin_manager.register(KelvinGroupDistribution())
