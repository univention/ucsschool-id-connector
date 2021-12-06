# -*- coding: utf-8 -*-

# Copyright 2021 Univention GmbH
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
from typing import Iterable

from ucsschool_id_connector.models import ListenerObject
from ucsschool_id_connector.plugins import hook_impl, plugin_manager
from ucsschool_id_connector.queues import InQueue
from ucsschool_id_connector.utils import ConsoleAndFileLogging

# That are all existing plugins for the id broker. If names change, this should be updated!
ID_BROKER_PLUGIN_NAMES = ("id_broker-users", "id_broker-groups")


class IDBrokerDistributionImpl:
    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)

    @hook_impl
    async def school_authorities_to_distribute_to(
        self, obj: ListenerObject, in_queue: InQueue
    ) -> Iterable[str]:
        """
        We ignore the school_authority mapping
        and sync objects for schools which have an ID Broker configuration.
        """
        s_a_names = set()
        s_a_names.update(
            [
                out_queue.school_authority.name
                for out_queue in in_queue.out_queues
                if any(plugin in ID_BROKER_PLUGIN_NAMES for plugin in out_queue.school_authority.plugins)
            ]
        )
        if s_a_names:
            self.logger.info(
                f"The changes are distributed to these school authorities, "
                f"since they are configured as id broker systems: {s_a_names}"
            )
        return s_a_names


plugin_manager.register(IDBrokerDistributionImpl())
