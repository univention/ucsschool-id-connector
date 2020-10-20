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

import pytest
from pydantic import ValidationError

import ucsschool_id_connector.models
import ucsschool_id_connector.queues


def test_command_with_valid_enum():
    ucsschool_id_connector.models.RPCRequest(cmd=ucsschool_id_connector.models.RPCCommand.get_queues)


def test_command_with_valid_str():
    ucsschool_id_connector.models.RPCRequest(cmd="get_queues")


def test_command_with_bad_str():
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(cmd="foo_bar")


def test_command_with_required_name_args():
    ucsschool_id_connector.models.RPCRequest(
        cmd=ucsschool_id_connector.models.RPCCommand.get_queue, name="foo"
    )
    ucsschool_id_connector.models.RPCRequest(
        cmd=ucsschool_id_connector.models.RPCCommand.get_school_authority, name="bar"
    )


def test_command_without_required_name_arg():
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(cmd=ucsschool_id_connector.models.RPCCommand.get_queue)
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_queue, name=""
        )
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_school_authority
        )
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.get_school_authority, name=""
        )


def test_command_with_required_school_authority_arg():
    ucsschool_id_connector.models.RPCRequest(
        cmd=ucsschool_id_connector.models.RPCCommand.create_school_authority,
        school_authority={"name": "foo", "url": "http://bar.baz", "password": "s3cr3t"},
    )


def test_command_without_required_school_authority_arg():
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.create_school_authority
        )
    with pytest.raises(ValidationError):
        ucsschool_id_connector.models.RPCRequest(
            cmd=ucsschool_id_connector.models.RPCCommand.create_school_authority,
            school_authority={},
        )
