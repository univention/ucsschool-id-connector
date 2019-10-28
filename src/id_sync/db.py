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
from typing import Type, TypeVar

from diskcache import Cache

from .models import ListenerOldDataEntry

ListenerOldDataEntryType = TypeVar(
    "ListenerOldDataEntryType", bound=ListenerOldDataEntry
)


class KeyValueDB:
    """Interface for concrete DB backend."""

    def __init__(self, datebase_dir: Path):
        if not datebase_dir.exists():
            datebase_dir.mkdir(mode=0o750, parents=True)
        self._cache = Cache(str(datebase_dir))

    def __contains__(self, key):
        return self._cache.__contains__(key)

    def __delitem__(self, key):
        return self._cache.__delitem__(key)

    def __getitem__(self, key):
        return self._cache.__getitem__(key)

    def __setitem__(self, key, value):
        return self._cache.__setitem__(key, value)

    def close(self, *args, **kwargs):
        return self._cache.close()

    def get(self, key, default=None, *args, **kwargs):
        return self._cache.get(key, default, *args, **kwargs)

    def set(self, key, value, *args, **kwargs):
        return self._cache.set(key, value, *args, **kwargs)

    def touch(self, *args, **kwargs):
        return self._cache.touch(*args, **kwargs)


class OldDataDB(KeyValueDB):
    """Typed wrapper of KeyValueDB"""

    def __init__(self, datebase_dir: Path, data_type: Type[ListenerOldDataEntryType]):
        super().__init__(datebase_dir)
        self._data_type = data_type

    def __getitem__(self, key: str) -> ListenerOldDataEntryType:
        return self._data_type(**super().__getitem__(key))

    def __setitem__(self, key: str, value: ListenerOldDataEntryType):
        return super().__setitem__(key, value.dict())

    def get(self, key, default=None, *args, **kwargs) -> ListenerOldDataEntryType:
        res = super().get(key, default, *args, **kwargs)
        if res is default:
            return default
        else:
            return self._data_type(**res)

    def set(self, key, value, *args, **kwargs):
        return super().set(key, value.dict(), *args, **kwargs)
