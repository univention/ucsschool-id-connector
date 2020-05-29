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
from typing import Any, Dict, List, Tuple, Union

import aiofiles
import aiohttp

from ucsschool_id_connector.constants import CHECK_SSL_CERTS
from ucsschool_id_connector.plugins import filter_plugins

ParamType = Union[Dict[str, str], List[Tuple[str, str]]]


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


async def _do_request(
    self,
    http_method: str,
    url,
    params: ParamType = None,
    acceptable_statuses: List[int] = None,
    data=None,
) -> Tuple[int, Dict[str, Any]]:
    acceptable_statuses = acceptable_statuses or [200]
    http_method = http_method.lower()
    meth = getattr(self._session, http_method)
    request_kwargs = {"url": url, "ssl": CHECK_SSL_CERTS}
    if http_method in {"patch", "post"} and data is not None:
        request_kwargs["json"] = data
    if params:
        request_kwargs["params"] = params
    hook_caller = filter_plugins(
        "create_request_kwargs", self.school_authority.postprocessing_plugins
    )
    for coro_result in hook_caller(
        http_method=http_method, url=url, school_authority=self.school_authority
    ):
        update_kwargs = await coro_result
        request_kwargs.update(update_kwargs)
    try:
        async with meth(**request_kwargs) as response:
            if response.status in acceptable_statuses:
                return (
                    response.status,
                    None if response.status == 204 else await response.json(),
                )
            else:
                self.logger.error(
                    "%s %r returned with status %r.",
                    http_method.upper(),
                    url,
                    response.status,
                )
                response_body = await self._get_error_msg(response)
                self.logger.error("Response body: %r", response_body)
                if len(response_body) > 500:
                    error_file = "/tmp/error.txt"  # nosec
                    async with aiofiles.open(error_file, "w") as fp:
                        await fp.write(response_body)
                    self.logger.error("Wrote response body to %r", error_file)
                msg = f"{http_method.upper()} {url} returned {response.status}."
                if response.status >= 500:
                    raise ServerError(msg, status=response.status)
                else:
                    raise APIRequestError(msg, status=response.status)
    except aiohttp.ClientConnectionError as exc:
        raise APICommunicationError(str(exc))


async def http_delete(
    self, url, acceptable_statuses: List[int] = None
) -> Tuple[int, Dict[str, Any]]:
    acceptable_statuses = acceptable_statuses or [204]
    return await self._do_request(
        http_method="delete", url=url, acceptable_statuses=acceptable_statuses
    )


async def http_get(
    self, url, params: ParamType = None, acceptable_statuses: List[int] = None
) -> Tuple[int, Dict[str, Any]]:
    return await self._do_request(
        http_method="get",
        url=url,
        acceptable_statuses=acceptable_statuses,
        params=params,
    )


async def http_patch(
    self, url, data, acceptable_statuses: List[int] = None
) -> Tuple[int, Dict[str, Any]]:
    acceptable_statuses = acceptable_statuses or [200]
    return await self._do_request(
        http_method="patch",
        url=url,
        data=data,
        acceptable_statuses=acceptable_statuses,
    )


async def http_post(
    self, url, data, acceptable_statuses: List[int] = None
) -> Tuple[int, Dict[str, Any]]:
    acceptable_statuses = acceptable_statuses or [201]
    return await self._do_request(
        http_method="post", url=url, data=data, acceptable_statuses=acceptable_statuses,
    )
