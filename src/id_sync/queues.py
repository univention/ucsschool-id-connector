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

import asyncio
import datetime
import os
import shutil
from pathlib import Path
from typing import AsyncIterator, Iterator, List, Optional, Set, TypeVar, Union

import aiofiles
import ujson
from aiojobs._job import Job
from aiojobs._scheduler import Scheduler

from .constants import (
    API_COMMUNICATION_ERROR_WAIT,
    IN_QUEUE_DIR,
    LOG_FILE_PATH_QUEUES,
    OUT_QUEUE_TOP_DIR,
    OUT_QUEUE_TRASH_DIR,
    UUID_DB_PATH,
)
from .ldap_access import LDAPAccess
from .models import (
    ListenerAddModifyObject,
    ListenerObject,
    ListenerOldDataEntry,
    ListenerRemoveObject,
    ListenerUserAddModifyObject,
    QueueModel,
    SchoolAuthorityConfiguration,
)
from .plugins import plugin_manager
from .user_handler import (
    APICommunicationError,
    ServerError,
    UnknownRole,
    UnknownSchool,
    UserHandler,
)
from .utils import ConsoleAndFileLogging, KeyValueDB

FileQueueTV = TypeVar("FileQueueTV", bound="FileQueue")


class InvalidListenerFile(Exception):
    pass


class ListenerLoadingError(Exception):
    pass


class ListenerSavingError(Exception):
    pass


class OldDataDB(KeyValueDB):
    """Typed wrapper of KeyValueDB"""

    def __getitem__(self, key: str) -> ListenerOldDataEntry:
        return ListenerOldDataEntry(**super().__getitem__(key))

    def __setitem__(self, key: str, value: ListenerOldDataEntry):
        return super().__setitem__(key, value.dict())

    def get(self, key, default=None, *args, **kwargs) -> ListenerOldDataEntry:
        return ListenerOldDataEntry(**super().get(key, default, *args, **kwargs))

    def set(self, key, value, *args, **kwargs):
        return super().set(key, value.dict(), *args, **kwargs)


class FileQueue:
    name: str
    path: Path
    head = ""
    school_authority: SchoolAuthorityConfiguration = None
    scheduler: Scheduler = None
    task: Job = None

    def __init__(self, name: str = None, path: Path = None) -> None:
        self.name = name or self.name
        self.path = path or self.path
        assert self.name
        assert self.path
        self.trash_dir = self.path / "trash"
        self.keep_dir = self.path / "keep"
        self._deleted = False
        self.logger = ConsoleAndFileLogging.get_logger(
            f"{self.__class__.__name__}({self.name})", LOG_FILE_PATH_QUEUES
        )
        self._last_alive_signal = 0
        try:
            self.path.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
        try:
            self.trash_dir.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
        try:
            self.keep_dir.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass

    def __len__(self) -> int:
        return len(list(self.queue_files()))

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r})"

    def queue_files(self, path: Path = None) -> List[Path]:
        """
        Sorted list of JSON files in `path` or :py:attr:`self.path`.

        :param Path path: path to list, if unset, self.path will be used
        :return: list of paths
        :rtype: list[Path]
        """
        res = []
        with os.scandir(
            path or self.path
        ) as dir_entries:  # type: Iterator[os.DirEntry]
            for entry in dir_entries:
                if entry.is_dir() and entry.name in ("keep", "trash"):
                    continue
                if not entry.is_file() or not entry.name.lower().endswith(".json"):
                    self.logger.warning(
                        "Non-JSON file found in queue %r: %r.", self.name, entry.name
                    )
                    self.discard_file(Path(entry.path))
                    continue
                res.append(Path(entry.path))
        return sorted(res)

    def as_queue_model(self):
        return QueueModel(
            name=self.name,
            head=self.head,
            length=len(self),
            school_authority=self.school_authority.name
            if self.school_authority
            else "",
        )

    async def start_task(
        self, method: str, ignore_inactive: bool = False, *args, **kwargs
    ):
        """Start `method` as a background task."""
        if self.scheduler is None:
            raise RuntimeError(
                f'Cannot start task for {self!r}, "scheduler" was not set.'
            )
        if self._deleted:
            raise RuntimeError(
                f"Cannot start task for {self!r}, queue directory has been deleted."
            )

        if not ignore_inactive and (
            not self.school_authority or not self.school_authority.active
        ):
            self.logger.warning("Starting task %r of inactive queue %r.", method, self)
        else:
            self.logger.debug(
                "Starting background task %r for queue %r...", method, self.name
            )
        meth = getattr(self, method)
        self.task = await self.scheduler.spawn(meth(*args, **kwargs))

    async def stop_task(self):
        if self.task and not self.task.closed:
            self.logger.info("Stopping my running background task...")
            await self.task.close()
        else:
            self.logger.info("No task running for me.")

    async def delete_queue(self):
        try:
            OUT_QUEUE_TRASH_DIR.mkdir(mode=0o750, parents=True)
        except FileExistsError:
            pass
        if self.task and not self.task.closed:
            await self.stop_task()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = OUT_QUEUE_TRASH_DIR / f"{timestamp}.{self.path.name}"
        # Bug in shutil.move(): https://bugs.python.org/issue32689
        shutil.move(str(self.path), str(target_dir))
        self._deleted = True
        self.logger.info("Moved directory %s to %s.", self.path, target_dir)

    def discard_file(self, path: Path) -> None:
        self.logger.debug("Moving %s to trash...", path.name)
        try:
            # Bug in shutil.move(): https://bugs.python.org/issue32689
            shutil.move(str(path), str(self.trash_dir))
        except FileNotFoundError:
            pass
        except (IOError, OSError) as exc:
            self.logger.error("Moving the file to trash: %s", exc)
            try:
                path.unlink()
            except (IOError, OSError, FileNotFoundError) as exc:
                self.logger.error("Deleting the file: %s", exc)

    def keep_file(self, path: Path) -> None:
        self.logger.debug("Moving %s to 'keep' directory...", path.name)
        try:
            shutil.move(str(path), str(self.keep_dir))
        except (FileNotFoundError, IOError, OSError) as exc:
            self.logger.error("Moving the file to 'keep' directory: %s", exc)

    async def load_listener_file(self, path: Path) -> ListenerObject:
        try:
            async with aiofiles.open(path, "r") as fp:
                obj_dict = ujson.loads(await fp.read())
        except (IOError, OSError, ValueError) as exc:
            self.logger.error("Loading %s: %s", path, exc)
            raise ListenerLoadingError(f"Loading {path.name} -> {exc}")
        listener_objects = plugin_manager.hook.get_listener_object(obj_dict=obj_dict)
        self.logger.debug(
            "Results from 'get_listener_object' hooks: %r", listener_objects
        )
        for obj in listener_objects:
            if obj:
                return obj
        else:
            raise ListenerLoadingError(
                "No result from 'get_listener_object' hook (listener_objects=%r) "
                "for obj_dict=%r",
                listener_objects,
                obj_dict,
            )

    async def save_listener_file(self, obj: ListenerObject, path: Path) -> None:
        # try:
        #     path = plugin_manager.hook.save_listener_object(obj=obj, path=path)
        # except (OSError, ValueError) as exc:
        #     self.logger.exception(
        #         "Saving obj to %s: %s\nobj=%r", path.name, exc, obj.dict()
        #     )
        #     raise ListenerSavingError(f"{path.name} -> {exc}")
        try:
            if isinstance(obj, ListenerUserAddModifyObject):
                json_text = ujson.dumps(
                    obj.dict_krb5_key_base64_encoded(), sort_keys=True, indent=4
                )
            else:
                json_text = ujson.dumps(obj.dict(), sort_keys=True, indent=4)
            async with aiofiles.open(path, "w") as fp:
                await fp.write(json_text)
        except Exception as exc:
            self.logger.exception(
                "Saving obj to %s: %s\nobj=%r", path.name, exc, obj.dict()
            )
            raise ListenerSavingError(f"{path.name} -> {exc}")

    def _signal_alive(self):
        now = datetime.datetime.now()
        if now.minute == 0 and self._last_alive_signal != now.hour:
            self._last_alive_signal = now.hour
            self.logger.debug("I'm alive.")


class InQueue(FileQueue):
    name = "InQueue"
    path = IN_QUEUE_DIR

    def __init__(
        self,
        name: Optional[str] = None,
        path: Optional[Path] = None,
        out_queues: Optional[List["OutQueue"]] = None,
    ) -> None:
        super(InQueue, self).__init__(name, path)
        self.logger.name = self.name
        self.out_queues = out_queues or []
        self._old_out_queues = {q.name for q in self.out_queues}
        self.old_date_db = OldDataDB(UUID_DB_PATH)
        self.ldap_access = LDAPAccess()

    @property
    def school_authority_names(self):
        return [q.school_authority.name for q in self.out_queues]

    async def preprocess_file(self, path: Path) -> Path:
        """
        Purging invalid files, storing and retrieving UUIDs and password
        hashes.

        :param Path path: path of listener file to analyze
        :return: new path if file was precessed sucessfully
        :raises InvalidListenerFile: if file contains invalid/incomplete data
        """
        try:
            obj = await self.load_listener_file(path)
        except ListenerLoadingError as exc:
            raise InvalidListenerFile(str(exc))

        # TODO: hook start
        if isinstance(obj, ListenerAddModifyObject):
            await self.preprocess_add_mod_object(obj, path)

        if isinstance(obj, ListenerRemoveObject):
            await self.preprocess_remove_object(obj, path)
        # TODO: hook end

        *dirs, name = path.parts
        name = name.rsplit(".", 1)[0]
        new_path = Path(*dirs, f"{name}_ready.json")
        path.rename(new_path)
        return new_path

    async def preprocess_add_mod_object(
        self, obj: ListenerAddModifyObject, path: Path
    ) -> None:
        """
        Preprocessing of create/modify-objects.

        Store (TODO: source_uid & record_uid?) in DB, so we can use it later when a user is
        modified or deleted (see `preprocess_remove_object()` and
        `distribute()`), because the ListenerAddModifyObject has no user data.
        """
        self.logger.debug("Preprocessing add/modify %r (%r)...", obj.dn, obj.id)
        # get old / store new data in (ListenerOldDataEntry) in self.old_date_db
        if isinstance(obj, ListenerUserAddModifyObject):
            # get passwords from ldap in case of ListenerUserAddModifyObject
            obj.user_passwords = await self.ldap_access.get_passwords(obj.username)
        try:
            await self.save_listener_file(obj, path)
        except ListenerSavingError as exc:
            raise InvalidListenerFile(str(exc))

    async def preprocess_remove_object(
        self, obj: ListenerRemoveObject, path: Path
    ) -> None:
        """
        Preprocessing of remove-objects.

        Get the users UUID from the DB.
        """
        self.logger.debug("Preprocessing remove %r (%r)...", obj.dn, obj.id)
        try:
            old_data = self.old_date_db[obj.id]
        except KeyError:
            self.logger.error("*** CANNOT DELETE USER FROM TARGET SYSTEM(S)! ***")
            self.logger.error(
                "No UUID stored for DN %r (entryUUID %r).", obj.dn, obj.id
            )
            raise InvalidListenerFile
        # User will be deleted, so data is useless now. Delete in 1 week (not
        # now), in case there was a problem and the data is still needed.
        self.old_date_db.touch(obj.id, expire=7 * 24 * 3600)
        # store old data in listener file
        # TODO: record_uid / source_uid ?
        try:
            await self.save_listener_file(obj, path)
        except ListenerSavingError as exc:
            raise InvalidListenerFile(str(exc))

    async def distribute_loop(self) -> None:
        """
        Main loop of in queue task: only preprocessing of JSON files. The
        actual distribution to out queues happend in :py:meth:`distribute()`.
        """
        self.logger.info("Distributing in-queue (%s)...", self.path)
        if list(self.out_queues):
            self.logger.info(
                "... to out queues %s.",
                ", ".join(repr(q.name) for q in self.out_queues),
            )
        else:
            self.logger.warning("No out queues configured!")
        while True:
            for path in (
                p for p in self.queue_files() if not p.name.endswith("_ready.json")
            ):
                try:
                    await self.preprocess_file(path)
                    self.logger.info("%s preprocessed.", path.name)
                except InvalidListenerFile as exc:
                    self.logger.info("Discarding invalid file %r: %s", path.name, exc)
                    self.discard_file(path)
                    continue
                except ListenerSavingError as exc:
                    self.logger.error("Could not save file %r: %s", path.name, exc)
                    self.discard_file(path)
                    continue
                except Exception as exc:
                    self.logger.exception(
                        "During preprocessing of file %r: %s", path.name, exc
                    )
                    raise InvalidListenerFile("Error during preprocessing.") from exc

            self.log_queue_changes()
            if self.out_queues:
                # Distribute only if out queues exist. Prevents deleting queue
                # files without consumers (out queues).
                await self.distribute()

            await asyncio.sleep(1)
            self._signal_alive()

    async def distribute(self, queue_paths: List[Path] = None) -> None:
        """
        Search for JSON files, extract school authorities and copy files to
        the respective out queues.

        :param list(Path) queue_paths: optional list of paths to look in for
            JSON files
        :return: None
        """
        queue_paths = queue_paths or (
            p for p in self.queue_files() if p.name.endswith("_ready.json")
        )
        for path in queue_paths:
            self.head = path.name
            try:
                obj = await self.load_listener_file(path)
                # distribute to school authorities
                # TODO: hook start (which school_authorities have to be contacted to handle this file?)
                s_a_names: Set[str] = set([])
                # await self.verify_school_authorities_are_known(s_a_names)
            except (ListenerLoadingError, InvalidListenerFile) as exc:
                # this shouldn't happen, as file has already been validated
                # except if not all school authorities are known...
                self.logger.info("Discarding invalid file %r: %s", path.name, exc)
                # TODO: don't remove if at least 1 known s_a
                self.discard_file(path)
                continue
            except Exception as exc:
                self.logger.exception("Unknown error: %s", exc)
                # TODO: don't remove if at least 1 known s_a
                self.discard_file(path)
                continue

            # add deleted school authorities, so the change/deletion will be
            # distributed by the respective out queues
            if isinstance(obj, ListenerAddModifyObject):
                # old_s_a = obj.old_data
                msg = "removed from user"
            else:
                # old_s_a = obj.new_data
                msg = "for removed user"
            deleted_s_a: Set["TODO"] = set([])
            if deleted_s_a:
                self.logger.debug(
                    "Found stored 'TODO' entries %s %r: %r",
                    msg,
                    obj.username,
                    deleted_s_a,
                )
            deleted_s_a_names = {s.school_authority for s in deleted_s_a}
            try:
                await self.verify_school_authorities_are_known(deleted_s_a_names)
                s_a_names.update(deleted_s_a_names)
            except InvalidListenerFile:
                self.logger.warning(
                    "Ignoring school authorities %r without out queue, found in removed "
                    "'TODO' entry.",
                    deleted_s_a_names,
                )
            # TODO: hook end

            # copy listener file to out queues for affected school authorities
            if not s_a_names:
                self.logger.info(
                    "Ignoring user without current or previous 'TODO... schools?' entries."
                )
            for out_queue in [
                out_queue
                for out_queue in self.out_queues
                if out_queue.school_authority.name in s_a_names
            ]:
                shutil.copy2(str(path), str(out_queue.path))
                self.logger.debug(
                    "Copied %r to out queue %r (%s).",
                    path.name,
                    out_queue.name,
                    "active" if out_queue.school_authority.active else "deactivated",
                )
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self.head = ""

    def log_queue_changes(self) -> None:
        current_queues = {q.name for q in self.out_queues}
        removed_queues = self._old_out_queues - current_queues
        if removed_queues:
            self.logger.debug(
                "Out queues have been removed: %s", ", ".join(removed_queues)
            )
        added_queues = current_queues - self._old_out_queues
        if added_queues:
            self.logger.debug("Out queues have been added: %s", ", ".join(added_queues))
        self._old_out_queues = current_queues

    # TODO: warning instead of error?
    async def verify_school_authorities_are_known(self, s_a_names: Set[str]) -> None:
        """
        :raises InvalidListenerFile: if file contains invalid/incomplete data
        """
        unknown_school_authority_names = s_a_names - set(self.school_authority_names)
        if unknown_school_authority_names:
            self.logger.error(
                "Unknown school authorities found: %r",
                sorted(unknown_school_authority_names),
            )
            raise InvalidListenerFile


class OutQueue(FileQueue):
    def __init__(
        self,
        name: str = None,
        path: Path = None,
        school_authority: SchoolAuthorityConfiguration = None,
    ) -> None:
        super(OutQueue, self).__init__(name, path)
        self.school_authority = school_authority
        # TODO: project specific handler class? GroupHandler?:
        self.user_handler = UserHandler(self.school_authority)

    async def scan(self) -> None:
        self.logger.info("Handling out queue %r (%s)...", self.name, self.path)
        while True:
            # in case of a communication error with the target API, sleep and retry
            try:
                await self.user_handler.fetch_roles()
                self.logger.debug(
                    "Roles known by API server: %s",
                    ", ".join(self.user_handler.api_roles_cache.keys()),
                )
                await self.user_handler.fetch_schools()
                self.logger.debug(
                    "Schools known by API server: %s",
                    ", ".join(self.user_handler.api_schools_cache.keys()),
                )
            except APICommunicationError as exc:
                self.logger.error(
                    "Error calling school authority API (retry in %d sec): %s",
                    API_COMMUNICATION_ERROR_WAIT,
                    exc,
                )
                await asyncio.sleep(API_COMMUNICATION_ERROR_WAIT)
            # communication is OK, handle queue
            while True:
                api_error = False
                for path in self.queue_files():
                    self.head = path.name
                    try:
                        await self.handle(path)
                    except (ServerError, UnknownSchool) as exc:
                        self.logger.error(exc)
                        self.discard_file(path)
                    except APICommunicationError as exc:
                        # continue in outer loop where we wait until communication is OK
                        self.logger.error("Error calling school authority API: %s", exc)
                        api_error = True
                        break
                    except Exception as exc:
                        self.logger.exception("Unhandled exception: %s", exc)
                        self.keep_file(path)
                    else:
                        # success - delete item from queue
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            pass
                if api_error:
                    break
                self.head = ""
                await asyncio.sleep(1)
                self._signal_alive()

    async def handle(self, path: Path) -> None:
        self.logger.debug("start handling %r.", path.name)
        try:
            obj = await self.load_listener_file(path)
        except ListenerLoadingError:
            self.logger.error("Error loading or invalid listener file %r.", path.name)
            self.discard_file(path)
            self.logger.debug("finished handling %r.", path.name)
            return
        # TODO: hook start (handle listener obj)
        try:
            if isinstance(obj, ListenerAddModifyObject):
                await self.user_handler.handle_create_or_update(obj)
            else:
                await self.user_handler.handle_remove(obj)
        except (UnknownSchool, UnknownRole) as exc:
            self.logger.error(exc)
            self.discard_file(path)
        # TODO: hook end
        self.logger.debug("finished handling %r.", path.name)

    @classmethod
    def from_school_authority(
        cls, school_authority: SchoolAuthorityConfiguration
    ) -> "OutQueue":
        logger = ConsoleAndFileLogging.get_logger(cls.__name__, LOG_FILE_PATH_QUEUES)
        res = cls(
            name=school_authority.name,
            path=OUT_QUEUE_TOP_DIR / school_authority.name,
            school_authority=school_authority,
        )
        logger.info("Created %r.", res)
        return res


async def get_out_queue_dirs() -> AsyncIterator[Path]:
    """
    List of directories in the our-queue basedir.

    :return: list of paths (AsyncIterator / coroutine)
    :rtype: AsyncIterator[Path]
    """
    try:
        OUT_QUEUE_TOP_DIR.mkdir(mode=0o750, parents=True)
    except FileExistsError:
        pass
    with os.scandir(OUT_QUEUE_TOP_DIR) as dir_entries:  # type: Iterator[os.DirEntry]
        for entry in dir_entries:
            if entry.is_dir():
                yield Path(entry.path)
