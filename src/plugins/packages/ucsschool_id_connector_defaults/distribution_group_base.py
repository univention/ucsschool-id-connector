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

import abc
from typing import Iterable, List

from ucsschool_id_connector.models import (
    ListenerGroupAddModifyObject,
    ListenerGroupRemoveObject,
    ListenerObject,
    SchoolAuthorityConfiguration,
)
from ucsschool_id_connector.plugins import hook_impl
from ucsschool_id_connector.queues import InQueue
from ucsschool_id_connector.utils import ConsoleAndFileLogging, school_class_dn_regex


class GroupDistributionImplBase(abc.ABC):
    """
    Base class to decide if and where to distribute school classes.

    Look for "implement this" comments to see what a subclass must contain.
    """

    plugin_name = "unknown plugin"  # implement this
    target_api_name = "unknown API"  # implement this

    def __init__(self):
        self.class_dn_regex = school_class_dn_regex()
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

        This method will only run pre-checks and then call
        `do_get_school_authorities_to_distribute_to` which subclasses should
        implement for their specific API.

        :param ListenerObject obj: of a concrete subclass of ListenerObject
        :param InQueue in_queue: the in-queue
        :return: list of names of school authorities, they should match those
            in ``SchoolAuthorityConfiguration.name``
        :rtype: list
        """
        if not isinstance(obj, ListenerGroupAddModifyObject) and not isinstance(
            obj, ListenerGroupRemoveObject
        ):
            return []

        group_match = self.class_dn_regex.match(obj.dn)
        if not group_match:
            self.logger.debug("Ignoring non-school_class group: %r", obj)
            return []

        school_authorities = self.school_authorities(in_queue)
        if not school_authorities:
            self.logger.debug(
                "Ignoring group: no SchoolAuthorityConfiguration for %s found.",
                self.target_api_name,
            )
            return []

        school_authority_names = {school_authority.name for school_authority in school_authorities}
        school_authority_ous = {
            ou.lower()
            for ou, s_a in in_queue.school_authority_mapping.items()
            if s_a in school_authority_names
        }
        group_ou = group_match.groupdict()["ou"]

        if group_ou.lower() in school_authority_ous:
            return [group_ou]
        else:
            self.logger.debug(
                "Ignoring group in OU %r that is not synced to any %r system: %r",
                group_ou,
                self.target_api_name,
                obj,
            )
            return []

    @classmethod
    def school_authorities(cls, in_queue: InQueue) -> List[SchoolAuthorityConfiguration]:
        return [
            out_queue.school_authority
            for out_queue in in_queue.out_queues
            if cls.plugin_name in out_queue.school_authority.plugins
        ]
