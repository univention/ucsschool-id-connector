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

import json
import logging
from unittest.mock import patch

from pydantic import SecretStr
from starlette.testclient import TestClient

import ucsschool_id_connector.constants
import ucsschool_id_connector.http_api
import ucsschool_id_connector.models
import ucsschool_id_connector.queues
import ucsschool_id_connector.token_auth
import ucsschool_id_connector.utils

client = TestClient(ucsschool_id_connector.http_api.app)


async def override_get_current_active_user():
    return ucsschool_id_connector.models.User(username="tester", disabled=False, dn="uid=tester,dc=test")


def override_setup_logging():
    logger = logging.getLogger("ucsschool_id_connector.http_api")
    ucsschool_id_connector.utils.ConsoleAndFileLogging.add_console_handler(logger)
    return logger


ucsschool_id_connector.http_api.app.dependency_overrides[
    ucsschool_id_connector.token_auth.get_current_active_user
] = override_get_current_active_user
ucsschool_id_connector.http_api.app.dependency_overrides[
    ucsschool_id_connector.http_api.get_logger
] = override_setup_logging


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_read_queues(zmq_context_mock, random_name, random_int, zmq_socket):
    queue_data = {
        "in_queue": {
            "name": random_name(),
            "head": random_name(),
            "length": random_int(),
        },
        "out_queues": [
            {"name": random_name(), "head": random_name(), "length": random_int()},
            {"name": random_name(), "head": random_name(), "length": random_int()},
        ],
    }
    socket = zmq_socket({"result": queue_data})
    zmq_context_mock.socket.return_value = socket
    res = client.get(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/queues",
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_queues
        ).json()
    )
    assert res.status_code == 200
    queue_data["in_queue"]["school_authority"] = ""
    queue_data["out_queues"][0]["school_authority"] = ""
    queue_data["out_queues"][1]["school_authority"] = ""
    assert res.json() == [queue_data["in_queue"], *queue_data["out_queues"]]


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_read_queue(zmq_context_mock, random_name, random_int, zmq_socket):
    queue_data = {"name": random_name(), "head": random_name(), "length": random_int()}
    socket = zmq_socket({"result": queue_data})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.get(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/queues/{queue_data['name']}",
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_queue,
            name=queue_data["name"],
        ).json()
    )
    assert res.status_code == 200
    queue_data["school_authority"] = ""
    assert res.json() == queue_data


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_read_school_authorities(zmq_context_mock, random_name, random_int, zmq_socket):
    school_authority_data = [
        {
            "name": random_name(),
            "active": bool(random_int(0, 1)),
            "url": f"http://{random_name()}.{random_name()}/",
            "plugins": ["bb"],
            "plugin_configs": {
                "bb": {"token": "foo", "passwords_target_attribute": random_name()},
            },
        },
        {
            "name": random_name(),
            "active": bool(random_int(0, 1)),
            "url": f"http://{random_name()}.{random_name()}/",
            "plugins": ["bb"],
            "plugin_configs": {
                "bb": {
                    "mapping": {
                        "school_classes": {random_name(): random_name()},
                        "users": {random_name(): random_name()},
                    },
                    "token": "foo",
                },
            },
        },
    ]
    socket = zmq_socket({"result": school_authority_data})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.get(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/school_authorities",
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_school_authorities
        ).json()
    )
    for data in school_authority_data:
        data["plugin_configs"]["bb"]["token"] = SecretStr("foo").display()  # '**********'
    assert res.status_code == 200
    res_json = res.json()
    school_authority_data.sort(key=lambda x: x["name"])
    assert res_json == school_authority_data


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_read_school_authority(zmq_context_mock, random_name, random_int, zmq_socket):
    school_authority_data = {
        "name": random_name(),
        "active": bool(random_int(0, 1)),
        "url": f"http://{random_name()}.{random_name()}/",
        "plugins": ["bb"],
        "plugin_configs": {
            "bb": {
                "mapping": {
                    "school_classes": {random_name(): random_name()},
                    "users": {random_name(): random_name()},
                },
                "token": random_name(),
                "passwords_target_attribute": random_name(),
            },
        },
    }
    socket = zmq_socket({"result": school_authority_data})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.get(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/school_authorities/"
        f"{school_authority_data['name']}",
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_school_authority,
            name=school_authority_data["name"],
        ).json()
    )
    assert res.status_code == 200
    school_authority_data["plugin_configs"]["bb"]["token"] = SecretStr("foo").display()  # '**********'
    assert res.json() == school_authority_data


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_create_school_authorities(zmq_context_mock, random_name, random_int, zmq_socket):
    # order matters in this dict, as socket.send_string.assert_called_with() below
    # compares the json representation
    school_authority_data = {
        "name": random_name(),
        "url": f"http://{random_name()}.{random_name()}/",
        "active": bool(random_int(0, 1)),
        "plugins": ["bb"],
        "plugin_configs": {
            "bb": {
                "mapping": {
                    "school_classes": {random_name(): random_name()},
                    "users": {random_name(): random_name()},
                },
                "token": random_name(),
                "passwords_target_attribute": random_name(),
            },
        },
    }
    socket = zmq_socket({"result": school_authority_data})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.post(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/school_authorities",
        json=school_authority_data,
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    args, kwargs = socket.send_string.call_args_list[0]
    call_kargs = json.loads(args[0])
    req_str = ucsschool_id_connector.models.RPCRequest(
        cmd=ucsschool_id_connector.models.RPCCommand.create_school_authority,
        school_authority=school_authority_data,
    ).json()
    req_obj = json.loads(req_str)
    assert call_kargs == req_obj
    assert res.status_code == 201
    school_authority_data["plugin_configs"]["bb"]["token"] = SecretStr("foo").display()  # '**********'
    assert res.json() == school_authority_data


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_read_school_to_school_authority_mapping(
    zmq_context_mock, zmq_socket, school2school_authority_mapping
):
    school_to_authority_mapping = school2school_authority_mapping()
    socket = zmq_socket({"result": school_to_authority_mapping.dict()})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.get(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/school_to_authority_mapping",
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_school_to_authority_mapping
        ).json()
    )
    assert res.status_code == 200
    assert res.json() == school_to_authority_mapping.dict()


@patch("ucsschool_id_connector.http_api.zmq_context")
def test_create_school_to_school_authority_mapping(
    zmq_context_mock,
    random_name,
    random_int,
    zmq_socket,
    school2school_authority_mapping,
):
    school_to_authority_mapping = school2school_authority_mapping()
    socket = zmq_socket({"result": school_to_authority_mapping.dict()})
    zmq_context_mock.socket.return_value = socket

    client = TestClient(ucsschool_id_connector.http_api.app)
    res = client.put(
        f"{ucsschool_id_connector.constants.URL_PREFIX}/school_to_authority_mapping",
        json=school_to_authority_mapping.dict(),
        timeout=4.0,
        headers={"Authorization": "Bearer TODO da token"},
    )
    socket.send_string.assert_called_with(
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.put_school_to_authority_mapping,
            school_to_authority_mapping=school_to_authority_mapping,
        ).json()
    )
    assert res.status_code == 200
    assert res.json() == school_to_authority_mapping.dict()


# TODO: test non-auth-access
# del ucsschool_id_connector.http_api. \
# app.dependency_overrides[ucsschool_id_connector.token.get_current_active_user] ?
