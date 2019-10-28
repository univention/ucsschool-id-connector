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

from pathlib import Path
from typing import Any, Dict, Optional, Type

import aiofiles
import ujson
from pydantic import ValidationError

from id_sync.constants import OLD_DATA_DB_PATH
from id_sync.db import OldDataDB
from id_sync.ldap_access import LDAPAccess
from id_sync.models import (
    ListenerAddModifyObject,
    ListenerGroupAddModifyObject,
    ListenerGroupOldDataEntry,
    ListenerGroupRemoveObject,
    ListenerObject,
    ListenerOldDataEntry,
    ListenerRemoveObject,
    ListenerUserAddModifyObject,
    ListenerUserOldDataEntry,
    ListenerUserRemoveObject,
)
from id_sync.plugins import hook_impl, plugin_manager
from id_sync.utils import ConsoleAndFileLogging


class ListenerObjectHandler:
    """
    Base class for handling the loading and saving of listener files with
    groups/group and users/user objects.
    """

    udm_object_type: str
    listener_add_modify_object_type: Type[ListenerAddModifyObject]
    listener_remove_object_type: Type[ListenerRemoveObject]
    listener_old_data_entry_type: Type[ListenerUserOldDataEntry]

    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__)
        self.old_data_db = OldDataDB(
            OLD_DATA_DB_PATH, self.listener_old_data_entry_type
        )

    @hook_impl
    def shutdown(self) -> None:
        """
        Called when the daemon is shutting down. Close database and network
        connections.
        """
        self.old_data_db.close()

    @hook_impl
    def get_listener_object(self, obj_dict: Dict[str, Any]) -> Optional[ListenerObject]:
        """
        Analyse `obj_dict` and return an instance of a subclass of
        `ListenerObject`. If the type cannot by recognized or should be
        handled by the default code, return `None`.

        Multiple `get_listener_object` hook implementations may run, until one
        returns an object. Further implementations will not be executed.

        :param dict obj_dict: dictionary loaded from the appcenter listener
            converters JSON file
        :return: `None` if not recognized, else instance of a subclass of `ListenerObject`
        :rtype: None or ListenerObject
        """
        udm_object_type = obj_dict.get("udm_object_type")
        if udm_object_type != self.udm_object_type:
            return None

        try:
            if obj_dict.get("object") is None:
                return self.listener_remove_object_type(**obj_dict)
            else:
                return self.listener_add_modify_object_type(**obj_dict)
        except ValidationError as exc:
            self.logger.exception("Loading obj_dict=%r : %s", obj_dict, exc)
            return None

    async def obj_as_dict(self, obj: ListenerObject) -> Dict[str, Any]:
        return obj.dict()

    @hook_impl
    async def save_listener_object(self, obj: ListenerObject, path: Path) -> bool:
        """
        Store `obj` JSON encoded into file at `path`.

        Multiple `get_listener_object` hook implementations may run, until one
        returns `True`. Further implementations will not be executed.

        :param ListenerObject obj: instance of a subclass of `ListenerObject`
        :param Path path: filesystem path to save to
        :return: whether the file was saved (False to let the default plugin handle it)
        :rtype: bool
        :raises ValueError: JSON encoding error
        :raises OSError: (FileNotFoundError etc)
        """
        if obj.udm_object_type != self.udm_object_type:
            return False

        obj_as_dict = await self.obj_as_dict(obj)
        json_text = ujson.dumps(obj_as_dict, sort_keys=True, indent=4)

        async with aiofiles.open(path, "w") as fp:
            await fp.write(json_text)
        return True

    def get_old_data(self, obj: ListenerObject) -> Optional[ListenerOldDataEntry]:
        """get previous 'old_data' from DB"""
        return self.old_data_db.get(obj.id)

    def save_old_data(self, obj: ListenerAddModifyObject) -> None:
        """save new 'old_data' to DB"""
        raise NotImplementedError

    @hook_impl
    async def preprocess_add_mod_object(self, obj: ListenerAddModifyObject) -> bool:
        """
        Preprocessing of create/modify-objects in the in queue.

        For example store data in a DB, that will not be available in the
        delete operation (use it in `preprocess_remove_object()`), because the
        ListenerRemoveObject has no object data, just the objects `id`. Or
        load additional data missing in the `obj.object`. Or if the difference
        to previous add/mod is needed in a modify operation.

        If `obj` was modified and the out queues should see that modification,
        return `True`, so it gets saved to disk.

        All `preprocess_add_mod_object` hook implementations will be executed.

        :param ListenerAddModifyObject obj: instance of a concrete subclass
            of ListenerAddModifyObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """
        if not isinstance(obj, self.listener_add_modify_object_type):
            return False

        # get old / store new data in self.old_data_db
        self.logger.debug("Preprocessing %r...", obj)
        obj.old_data = self.get_old_data(obj)
        self.save_old_data(obj)
        return bool(obj.old_data)

    @hook_impl
    async def preprocess_remove_object(self, obj: ListenerRemoveObject) -> bool:
        """
        Preprocessing of remove-objects in the in queue.

        For example get the users previous IDs etc from a DB, as the
        ListenerRemoveObject has no object data.

        If `obj` was modified and the out queues should see that modification,
        return `True`, so it gets saved to disk.

        All `preprocess_remove_object` hook implementations will be executed.

        :param ListenerRemoveObject obj: instance of a concrete subclass
            of ListenerRemoveObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """
        if not isinstance(obj, self.listener_remove_object_type):
            return False

        self.logger.debug("Preprocessing %r...", obj)
        obj.old_data = self.get_old_data(obj)
        if obj.old_data:
            # User will be deleted, so data is useless now. Delete in 1 week (not
            # now), in case there was a problem and the data is still needed.
            self.old_data_db.touch(obj.id, expire=7 * 24 * 3600)
            return True
        else:
            self.logger.error("*** CANNOT DELETE OBJECT FROM TARGET SYSTEM(S)! ***")
            self.logger.error(
                "No previous data stored for DN %r (entryUUID %r).", obj.dn, obj.id
            )
            return False


class ListenerUserObjectHandler(ListenerObjectHandler):
    """Handle loading and saving of listener files with users/user objects."""

    udm_object_type = "users/user"
    listener_add_modify_object_type = ListenerUserAddModifyObject
    listener_remove_object_type = ListenerUserRemoveObject
    listener_old_data_entry_type = ListenerUserOldDataEntry

    def __init__(self):
        super().__init__()
        self.ldap_access = LDAPAccess()

    async def obj_as_dict(self, obj: ListenerObject) -> Dict[str, Any]:
        if isinstance(obj, ListenerUserAddModifyObject):
            obj_as_dict = obj.dict_krb5_key_base64_encoded()
        else:
            obj_as_dict = obj.dict()
        if isinstance(obj, ListenerUserAddModifyObject) or isinstance(
            obj, ListenerUserRemoveObject
        ):
            if obj_as_dict.get("old_data") == {}:
                # prevent validation error when loading into
                # ListenerUserAddModifyObject or ListenerUserRemoveObject
                del obj_as_dict["old_data"]
        return obj_as_dict

    def save_old_data(self, obj: ListenerUserAddModifyObject) -> None:
        self.old_data_db[obj.id] = ListenerUserOldDataEntry(
            schools=obj.schools, record_uid=obj.record_uid, source_uid=obj.source_uid
        )

    @hook_impl
    async def preprocess_add_mod_object(self, obj: ListenerUserAddModifyObject) -> bool:
        if not isinstance(obj, self.listener_add_modify_object_type):
            return False
        old_data_res = await super().preprocess_add_mod_object(obj)
        obj.user_passwords = await self.ldap_access.get_passwords(obj.username)
        if not obj.user_passwords:
            self.logger.error("Could not get password hashes of %r.", obj.dn)
        return old_data_res or bool(obj.user_passwords)


class ListenerGroupObjectHandler(ListenerObjectHandler):
    """Handle loading and saving of listener files with groups/group objects."""

    udm_object_type = "groups/group"
    listener_add_modify_object_type = ListenerGroupAddModifyObject
    listener_remove_object_type = ListenerGroupRemoveObject
    listener_old_data_entry_type = ListenerGroupOldDataEntry

    def save_old_data(self, obj: ListenerGroupAddModifyObject) -> None:
        """save new 'old_data' to DB"""
        self.old_data_db[obj.id] = ListenerGroupOldDataEntry(users=obj.users)


# hooks will be executed in the reversed order they were registered
plugin_manager.register(ListenerGroupObjectHandler())
plugin_manager.register(ListenerUserObjectHandler())
