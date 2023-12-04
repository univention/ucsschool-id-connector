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

import datetime
from pathlib import Path
from typing import Optional

import aiofiles
import ujson

from ucsschool_id_connector.constants import APPCENTER_LISTENER_PATH
from ucsschool_id_connector.ldap_access import LDAPAccess
from ucsschool_id_connector.models import Group
from ucsschool_id_connector.utils import ConsoleAndFileLogging


class GroupScheduler:
    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self.ldap_access = LDAPAccess()

    async def get_group_from_ldap(self, groupname: str) -> Optional[Group]:
        return await self.ldap_access.get_group(groupname, attributes=["*", "entryUUID"])

    @staticmethod
    async def write_listener_file(group: Group) -> None:
        """
        Create JSON file to trigger appcenter converter service to create JSON
        file for our app container.

        We cannot create listener files (`ListenerObject`) like the appcenter
        converter service does, because we don't have UDM. So we'll create the
        files the appcenter listener creates. They will trigger the appcenter
        converter service to write the listener files (`ListenerObject`).

        This is what the appcenter listener does in
        management/univention-appcenter/python/appcenter/listener.py in
        `AppListener._write_json()`.
        """
        attrs = {
            "entry_uuid": group.attributes["entryUUID"][0],
            "dn": group.dn,
            "object_type": "groups/group",
            "command": "m",
        }
        json_s = ujson.dumps(attrs, sort_keys=True, indent=4)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        path = Path(APPCENTER_LISTENER_PATH, f"{timestamp}.json")
        async with aiofiles.open(path, "w") as fp:
            await fp.write(json_s)

    async def queue_group(self, groupname: str) -> None:
        self.logger.debug("Searching LDAP for group with groupname %r...", groupname)
        group = await self.get_group_from_ldap(groupname)
        if group:
            self.logger.info("Adding group to in-queue: %r.", group.dn)
            await self.write_listener_file(group)
        else:
            self.logger.error("No school group with groupname %r could be found.", groupname)
