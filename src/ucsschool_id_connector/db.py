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

import abc
from pathlib import Path
from typing import Any, Generic, Type, TypeVar, Union, cast

from diskcache import Cache

from .models import ListenerOldDataEntry

NativeType = TypeVar("NativeType")
StorageType = TypeVar("StorageType")
ListenerOldDataEntryType = TypeVar("ListenerOldDataEntryType", bound=ListenerOldDataEntry)


class KeyValueDB(Generic[NativeType, StorageType], abc.ABC):
    """Interface for concrete DB backend."""

    _native_type: NativeType
    _storage_type: StorageType

    def __init__(self, datebase_dir: Path):
        if not datebase_dir.exists():
            datebase_dir.mkdir(mode=0o750, parents=True)
        self._cache = Cache(str(datebase_dir))

    def __contains__(self, key: Any) -> bool:
        return self._cache.__contains__(key)

    def __delitem__(self, key: Any) -> bool:
        return self._cache.__delitem__(key)

    def __getitem__(self, key: Any) -> NativeType:
        return self._storage_to_native_type(self._cache.__getitem__(key))

    def __setitem__(self, key: Any, value: NativeType) -> None:
        return self._cache.__setitem__(key, self._native_to_storage_type(value))

    def _native_to_storage_type(self, value: NativeType) -> StorageType:
        if self._native_type is self._storage_type or self._storage_type is None:
            return cast(StorageType, value)
        else:
            return self._storage_type(value)

    def _storage_to_native_type(self, value: StorageType) -> NativeType:
        if self._native_type is self._storage_type or self._native_type is None:
            return cast(NativeType, value)
        else:
            return self._native_type(value)

    def close(self, *args, **kwargs) -> None:
        return self._cache.close()

    def get(self, key: Any, default: Any = None, *args, **kwargs) -> Union[Any, NativeType]:
        value = self._cache.get(key, default, *args, **kwargs)
        if value is default:
            return default
        else:
            return self._storage_to_native_type(value)

    def set(self, key: Any, value: NativeType, *args, **kwargs) -> bool:
        return self._cache.set(key, self._native_to_storage_type(value), *args, **kwargs)

    def touch(self, *args, **kwargs) -> bool:
        return self._cache.touch(*args, **kwargs)


class OldDataDB(KeyValueDB):
    """Wrapper of KeyValueDB typed to a specific ListenerOldDataEntryType subclass"""

    _native_type = ListenerOldDataEntryType
    _storage_type = dict

    def __init__(self, datebase_dir: Path, data_type: Type[ListenerOldDataEntryType]):
        super().__init__(datebase_dir)
        self._native_type = data_type

    def _native_to_storage_type(self, value: ListenerOldDataEntryType) -> dict:
        return value.dict()

    def _storage_to_native_type(self, value: dict) -> ListenerOldDataEntryType:
        return self._native_type(**value)
