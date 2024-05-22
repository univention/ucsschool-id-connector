# -*- coding: utf-8 -*-

# Copyright 2020 Univention GmbH
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

import logging
import ssl
from typing import Match

import httpx
import lazy_object_proxy

from ucsschool.kelvin.client import Session
from ucsschool_id_connector.constants import HTTP_REQUEST_TIMEOUT
from ucsschool_id_connector.models import SchoolAuthorityConfiguration
from ucsschool_id_connector.utils import ConsoleAndFileLogging, kelvin_url_regex

logger: logging.Logger = lazy_object_proxy.Proxy(lambda: ConsoleAndFileLogging.get_logger(__name__))


def kelvin_client_session(school_authority: SchoolAuthorityConfiguration, plugin_name: str) -> Session:
    m: Match = kelvin_url_regex().match(school_authority.url)
    if not m:
        raise ValueError(
            f"Bad Kelvin URL in school authority {school_authority!r}: {school_authority.url!r}."
        )
    host = m.groupdict()["host"]
    try:
        username = school_authority.plugin_configs[plugin_name]["username"]
        password = school_authority.plugin_configs[plugin_name]["password"].get_secret_value()
    except KeyError as exc:
        raise ValueError(
            f"Missing {exc!s} in Kelvin plugin configuration of school authority "
            f"{school_authority.dict()!r}."
        )
    timeout = httpx.Timeout(timeout=HTTP_REQUEST_TIMEOUT)
    ssl_context: ssl.SSLContext = httpx.create_ssl_context()
    for k, v in school_authority.plugin_configs[plugin_name].get("ssl_context", {}).items():
        logger.info("Applying to SSL context: %r=%r", k, v)
        setattr(ssl_context, k, v)
    return Session(
        username=username,
        password=password,
        host=host,
        verify=ssl_context,
        timeout=timeout,
    )
