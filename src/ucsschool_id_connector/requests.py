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

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import aiofiles
import aiohttp
import lazy_object_proxy

from ucsschool_id_connector.constants import (
    CHECK_SSL_CERTS,
    HTTP_CLIENT_TIMEOUT,
    LOG_FILE_PATH_QUEUES,
)
from ucsschool_id_connector.plugins import filter_plugins
from ucsschool_id_connector.utils import ConsoleAndFileLogging

ParamType = Union[Dict[str, str], List[Tuple[str, str]]]
logger: logging.Logger = lazy_object_proxy.Proxy(
    lambda: ConsoleAndFileLogging.get_logger(__name__, LOG_FILE_PATH_QUEUES)
)


class APICommunicationError(Exception):
    pass


class APIRequestError(APICommunicationError):
    def __init__(self, *args, status: int, **kwargs):
        self.status = status
        super().__init__(*args, **kwargs)


class ServerError(APICommunicationError):
    def __init__(self, *args, status: int, **kwargs):
        self.status = status
        super().__init__(*args, **kwargs)


async def _get_error_msg(
    response: aiohttp.ClientResponse,
) -> Union[Dict[str, Any], str]:
    try:
        return await response.json()
    except (ValueError, aiohttp.ContentTypeError):
        return await response.text()


async def _do_request(  # noqa: C901
    http_method: str,
    url,
    school_authority,
    params: ParamType = None,
    acceptable_statuses: List[int] = None,
    data=None,
    session=None,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    acceptable_statuses = acceptable_statuses or [200]
    http_method = http_method.lower()
    if session:
        session_to_use = session
    else:
        timeout = aiohttp.ClientTimeout(total=HTTP_CLIENT_TIMEOUT)
        session_to_use = aiohttp.ClientSession(timeout=timeout)
    meth = getattr(session_to_use, http_method)
    request_kwargs = {"url": url, "ssl": CHECK_SSL_CERTS}
    if http_method in {"patch", "post"} and data is not None:
        request_kwargs["json"] = data
    if params:
        request_kwargs["params"] = params
    create_request_kwargs_caller = filter_plugins(
        "create_request_kwargs", school_authority.plugins
    )
    for update_kwargs in await asyncio.gather(
        *create_request_kwargs_caller(
            http_method=http_method, url=url, school_authority=school_authority
        )
    ):
        request_kwargs.update(update_kwargs)
    try:
        async with meth(**request_kwargs) as response:
            if not session:
                await session_to_use.close()
            if response.status in acceptable_statuses:
                return (
                    response.status,
                    None if response.status == 204 else await response.json(),
                )
            else:
                logger.error(
                    "%s %r returned with status %r.",
                    http_method.upper(),
                    url,
                    response.status,
                )
                response_body = await _get_error_msg(response)
                logger.error("Response body: %r", response_body)
                if len(response_body) > 500:
                    error_file = "/tmp/error.txt"  # nosec
                    async with aiofiles.open(error_file, "w") as fp:
                        await fp.write(response_body)
                    logger.error("Wrote response body to %r", error_file)
                msg = f"{http_method.upper()} {url} returned {response.status}."
                if response.status >= 500:
                    raise ServerError(msg, status=response.status)
                else:
                    raise APIRequestError(msg, status=response.status)
    except aiohttp.ClientConnectionError as exc:
        raise APICommunicationError(str(exc))


async def http_delete(
    url, school_authority, acceptable_statuses: List[int] = None, session=None
) -> Tuple[int, Optional[Dict[str, Any]]]:
    acceptable_statuses = acceptable_statuses or [204]
    return await _do_request(
        http_method="delete",
        url=url,
        school_authority=school_authority,
        acceptable_statuses=acceptable_statuses,
        session=session,
    )


async def http_get(
    url,
    school_authority,
    params: ParamType = None,
    acceptable_statuses: List[int] = None,
    session=None,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    return await _do_request(
        http_method="get",
        url=url,
        school_authority=school_authority,
        acceptable_statuses=acceptable_statuses,
        params=params,
        session=session,
    )


async def http_patch(
    url, school_authority, data, acceptable_statuses: List[int] = None, session=None,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    acceptable_statuses = acceptable_statuses or [200]
    return await _do_request(
        http_method="patch",
        url=url,
        school_authority=school_authority,
        data=data,
        acceptable_statuses=acceptable_statuses,
        session=session,
    )


async def http_post(
    url, school_authority, data, acceptable_statuses: List[int] = None, session=None,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    acceptable_statuses = acceptable_statuses or [201]
    return await _do_request(
        http_method="post",
        url=url,
        school_authority=school_authority,
        data=data,
        acceptable_statuses=acceptable_statuses,
        session=session,
    )
