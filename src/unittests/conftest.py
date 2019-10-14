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
import random
import string
from functools import partial
from unittest.mock import MagicMock

import pytest
import ujson


@pytest.fixture
def random_name():
    def _func():
        name = list(string.ascii_letters + string.digits)
        random.shuffle(name)
        return "".join(name[: random.randint(8, 12)])

    return _func


@pytest.fixture
def random_int():
    def _func(start=0, end=12):
        return random.randint(start, end)

    return _func


@asyncio.coroutine
def recv_string(obj):
    yield from asyncio.sleep(0.1)
    return ujson.dumps(obj)


@pytest.fixture
def zmq_socket():
    def _func(recv_string_args):
        socket = MagicMock()
        socket.send_string.return_value = {}
        socket.recv_string = partial(recv_string, recv_string_args)
        return socket

    return _func
