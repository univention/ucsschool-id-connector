from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
import ujson
from pydantic import ValidationError

from id_sync.models import (
    ListenerObject,
    ListenerRemoveObject,
    ListenerUserAddModifyObject,
)
from id_sync.plugins import hook_impl, plugin_manager
from id_sync.utils import ConsoleAndFileLogging

logger = ConsoleAndFileLogging.get_logger("plugins." + __name__)


class ListenerObjectHandler:
    """Handle loading and saving of listener files."""

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
                return ListenerRemoveObject(**obj_dict)
            else:
                return ListenerUserAddModifyObject(**obj_dict)
        except ValidationError as exc:
            logger.exception("Loading obj_dict=%r : %s", obj_dict, exc)
            return None

    # @hook_impl
    # def save_listener_object(self, obj: ListenerObject, path: Path) -> bool:
    #     """
    #     Store `obj` JSON encoded into file at `path`.
    #
    #     :param ListenerObject obj: instance of a subclass of `ListenerObject`
    #     :param Path path: filesystem path to save to
    #     :return: whether the file was saved (False to let the default plugin handle it)
    #     :rtype: bool
    #     :raises ValueError: JSON encoding error
    #     :raises OSError: (FileNotFoundError etc)
    #     """
    #     if obj.udm_object_type != "users/user":
    #         logger.debug("Ignoring %r object.", obj.udm_object_type)
    #         return False
    #
    #     if isinstance(obj, ListenerUserAddModifyObject):
    #         json_text = ujson.dumps(
    #             obj.dict_krb5_key_base64_encoded(), sort_keys=True, indent=4
    #         )
    #     else:
    #         json_text = ujson.dumps(obj.dict(), sort_keys=True, indent=4)
    #
    #     async with aiofiles.open(path, "w") as fp:
    #         await fp.write(json_text)
    #     return True


# register plugin
plugin_manager.register(ListenerObjectHandler())
