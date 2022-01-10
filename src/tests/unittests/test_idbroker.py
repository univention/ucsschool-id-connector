# -*- coding: utf-8 -*-

# Copyright 2021 Univention GmbH
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
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import ucsschool_id_connector.plugin_loader
import ucsschool_id_connector.token_auth

pytestmark = [pytest.mark.id_broker, pytest.mark.usefixtures("mock_plugins")]


@patch("ucsschool_id_connector.token_auth.get_secret_key", AsyncMock(return_value="Foo"))
@pytest.mark.asyncio
async def test_current_token_is_valid():
    from idbroker import id_broker_client  # isort:skip  # noqa: E402
    from idbroker.provisioning_api import Token as GenToken  # isort:skip # noqa: E402

    access_token = await ucsschool_id_connector.token_auth.create_access_token(
        data={"sub": "bar"}, expires_delta=datetime.timedelta(minutes=60)
    )
    token = id_broker_client.Token(MagicMock())
    token._token = GenToken(access_token, "None")
    token._token._access_token = access_token
    token._token_expiry = token._token_expiration(access_token)
    a_t = await token.access_token
    assert a_t == access_token


@patch("ucsschool_id_connector.token_auth.get_secret_key", AsyncMock(return_value="Foo"))
@pytest.mark.asyncio
async def test_token_fetch_expired_token():
    from idbroker import id_broker_client  # isort:skip  # noqa: E402
    from idbroker.provisioning_api import Token as GenToken  # isort:skip # noqa: E402

    access_token = await ucsschool_id_connector.token_auth.create_access_token(
        data={"sub": "bar"}, expires_delta=datetime.timedelta(minutes=-6)
    )
    token = id_broker_client.Token(MagicMock())
    token._fetch_token = AsyncMock(return_value=GenToken(access_token, "None"))
    with pytest.raises(ValueError) as exc:
        await token.access_token
        assert exc.match("Retrieved expired token")


@patch("ucsschool_id_connector.token_auth.get_secret_key", AsyncMock(return_value="Foo"))
@pytest.mark.asyncio
async def test_token_gets_refreshed():
    from idbroker import id_broker_client  # isort:skip  # noqa: E402
    from idbroker.provisioning_api import Token as GenToken  # isort:skip # noqa: E402

    access_token = await ucsschool_id_connector.token_auth.create_access_token(
        data={"sub": "bar"}, expires_delta=datetime.timedelta(seconds=2)
    )
    token = id_broker_client.Token(MagicMock())
    # token._access_token = access_token
    token._token = GenToken(access_token, "None")
    token._token._access_token = access_token
    token._token_expiry = token._token_expiration(access_token)
    token._fetch_token = AsyncMock(return_value=GenToken(access_token, "None"))
    # this should work:
    await token.access_token
    time.sleep(3)
    with pytest.raises(ValueError) as exc:
        await token.access_token
        # as we replaced Token._fetch_token(), the same (now expired) Token will be returned by it
        assert exc.match("Retrieved expired token")
