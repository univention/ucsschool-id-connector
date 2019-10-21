from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
import ujson
from pydantic import ValidationError

from id_sync.models import (
    ListenerObject,
    ListenerAddModifyObject,
    ListenerRemoveObject,
    ListenerUserAddModifyObject,
    ListenerUserRemoveObject,
    ListenerUserOldDataEntry,
)
from id_sync.constants import OLD_DATA_DB_PATH
from id_sync.db import OldDataDB
from id_sync.ldap_access import LDAPAccess
from id_sync.plugins import hook_impl, plugin_manager
from id_sync.utils import ConsoleAndFileLogging

logger = ConsoleAndFileLogging.get_logger("plugins." + __name__)


class ListenerObjectHandler:
    """Handle loading and saving of listener files."""

    def __init__(self):
        self.old_data_db = OldDataDB(OLD_DATA_DB_PATH, ListenerUserOldDataEntry)
        self.ldap_access = LDAPAccess()

    @hook_impl
    def get_listener_object(self, obj_dict: Dict[str, Any]) -> Optional[ListenerObject]:
        """
        Analyse `obj_dict` and return an instance of a subclass of
        `ListenerObject`. If the type cannot by recognized or should be
        handled by the default code, return `None`.

        :param dict obj_dict: dictionary loaded from the appcenter listener
            converters JSON file
        :return: `None` if not object was not recognized, else an instance of
            a subclass of `ListenerObject`
        :rtype: None or ListenerObject
        """
        udm_object_type = obj_dict.get("udm_object_type")
        if udm_object_type != "users/user":
            logger.debug("Ignoring %r object.", udm_object_type)
            return None

        try:
            if obj_dict.get("object") is None:
                return ListenerUserRemoveObject(**obj_dict)
            else:
                return ListenerUserAddModifyObject(**obj_dict)
        except ValidationError as exc:
            logger.exception("Loading obj_dict=%r : %s", obj_dict, exc)
            return None

    @hook_impl
    async def save_listener_object(self, obj: ListenerObject, path: Path) -> bool:
        """
        Store `obj` JSON encoded into file at `path`.

        :param ListenerObject obj: instance of a subclass of `ListenerObject`
        :param Path path: filesystem path to save to
        :return: whether the file was saved (False to let the default plugin handle it)
        :rtype: bool
        :raises ValueError: JSON encoding error
        :raises OSError: (FileNotFoundError etc)
        """
        if obj.udm_object_type != "users/user":
            logger.debug("Ignoring %r object.", obj.udm_object_type)
            return False

        if isinstance(obj, ListenerUserAddModifyObject):
            obj_as_dict = obj.dict_krb5_key_base64_encoded()
        else:
            obj_as_dict = obj.dict()
        if isinstance(obj, ListenerUserAddModifyObject) or isinstance(obj, ListenerUserRemoveObject):
            if obj_as_dict.get("old_data") == {}:
                # prevent validation error when loading into
                # ListenerUserAddModifyObject or ListenerUserRemoveObject
                del obj_as_dict["old_data"]
        json_text = ujson.dumps(obj_as_dict, sort_keys=True, indent=4)

        async with aiofiles.open(path, "w") as fp:
            await fp.write(json_text)
        return True

    @hook_impl
    async def preprocess_add_mod_object(self, obj: ListenerAddModifyObject) -> bool:
        """
        Preprocessing of create/modify-objects in the in queue.

        For example store data in a DB, that will not be available in the
        delete operation (use it in `preprocess_remove_object()`), because the
        ListenerRemoveObject has no object data, just the objects `id`. Or
        load additional data missing in the `obj.object`.

        If `obj` was modified and the out queues should see that modification,
        return `True`, so it gets saved to disk.

        All `preprocess_add_mod_object` hook implementations will be executed.

        :param ListenerAddModifyObject obj: instance of a concrete subclass
            of ListenerAddModifyObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """
        # get old / store new data in (ListenerUserOldDataEntry) in self.old_date_db
        if isinstance(obj, ListenerUserAddModifyObject):
            logger.debug("Preprocessing add/modify %r (%r)...", obj.dn, obj.id)
            # get previous 'old_data' from DB, so we can know if a school was
            # removed from the user
            try:
                obj.old_data = self.old_data_db[obj.id]
            except KeyError:
                pass
            # get passwords from ldap and update 'old_data' in DB
            obj.user_passwords = await self.ldap_access.get_passwords(obj.username)
            self.old_data_db[obj.id] = ListenerUserOldDataEntry(
                schools=obj.schools,
                record_uid=obj.object.get("record_uid"),
                source_uid=obj.object.get("source_uid"),
            )
            return True
        return False

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
            of ListenerAddModifyObject
        :return: whether `obj` was modified and it should be written back to
            the listener file, so out queues can load it.
        :rtype: bool
        """
        if isinstance(obj, ListenerUserRemoveObject):
            try:
                obj.old_data = self.old_data_db[obj.id]
            except KeyError:
                logger.error("*** CANNOT DELETE USER FROM TARGET SYSTEM(S)! ***")
                logger.error(
                    "No previous schools etc. stored for DN %r (entryUUID %r).", obj.dn, obj.id
                )
            else:
                # User will be deleted, so data is useless now. Delete in 1 week (not
                # now), in case there was a problem and the data is still needed.
                self.old_data_db.touch(obj.id, expire=7 * 24 * 3600)
                return True
        return False


# register plugin
plugin_manager.register(ListenerObjectHandler())
