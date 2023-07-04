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

import asyncio
import pprint
from typing import Iterator, List, Optional

import ujson
import zmq
import zmq.asyncio
from aiojobs._job import Job
from pydantic import ValidationError

from .config_storage import ConfigurationStorage
from .constants import LOG_FILE_PATH_QUEUES
from .models import (
    AllQueues,
    NoObjectError,
    ObjectExistsError,
    RPCCommand,
    RPCRequest,
    RPCResponseModel,
    School2SchoolAuthorityMapping,
    SchoolAuthorityConfiguration,
    SchoolAuthorityConfigurationPatchDocument,
)
from .queues import InQueue, OutQueue
from .utils import ConsoleAndFileLogging


class UnknownRPCCommand(Exception):
    pass


class SimpleRPCServer:
    def __init__(self, addr: str, in_queue: InQueue, out_queues: List[OutQueue]):
        self.addr = addr
        self.in_queue = in_queue
        self.out_queues = out_queues
        self.task: Optional[Job] = None
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__, LOG_FILE_PATH_QUEUES)
        context = zmq.asyncio.Context()
        self.socket = context.socket(zmq.REP)

    @property
    def active_out_queues(self) -> Iterator[OutQueue]:
        return (q for q in self.out_queues if q.school_authority.active)

    async def start_out_queue_task(self, out_queue: OutQueue):
        """
        Start out queue background task if `out_queue.school_authority.active`
        is True.
        """
        if out_queue.school_authority.active:
            self.logger.info(
                "Starting out queue background task for school authority %r...",
                out_queue.school_authority.name,
            )
            await out_queue.start_task("scan")
        else:
            self.logger.info(
                "Not starting out queue tasks for deactivated school authority %r.",
                out_queue.school_authority.name,
            )

    async def save_school_authority_configuration(self, out_queue: OutQueue):
        self.logger.info(
            "Saving school authority configuration %r...",
            out_queue.school_authority.name,
        )
        await ConfigurationStorage.save_school_authorities([out_queue.school_authority])

    @asyncio.coroutine
    def simple_rpc_server(self) -> None:
        self.socket.bind(self.addr)
        self.logger.info("RPC server listening on %r.", self.addr)
        while True:
            message = yield from self.socket.recv_string()
            # self.logger.debug("Received: %r", message)
            try:
                req = ujson.loads(message)
                req["cmd"] = RPCCommand(req.get("cmd"))
                request = RPCRequest(**req)
                response = yield from self.handle_request(request)
            except TypeError as exc:
                response = RPCResponseModel(
                    errors=[
                        {
                            "loc": ("errors", 0),
                            "msg": f"TypeError: {exc}",
                            "type": "general",
                        }
                    ]
                )
            except ValidationError as exc:
                response = RPCResponseModel(errors=exc.errors())
            except (ObjectExistsError, NoObjectError) as exc:
                response = RPCResponseModel(
                    errors=[
                        {
                            "loc": ("errors", 0),
                            "msg": f"{type(exc).__name__}: {exc}",
                            "type": "general",
                        }
                    ]
                )
            except UnknownRPCCommand as exc:
                self.logger.exception(exc)
                response = RPCResponseModel(
                    errors=[{"loc": ("body", 0), "msg": str(exc), "type": "general"}]
                )
            except Exception as exc:
                self.logger.exception("Error handling message %r: %s", message, exc)
                response = RPCResponseModel(
                    errors=[
                        {
                            "loc": ("errors", 0),
                            "msg": f"Unknown error: {exc}",
                            "type": "general",
                        }
                    ]
                )
            response_msg = response.json()
            # self.logger.debug("Sending: %r", response_msg)
            yield from self.socket.send_string(response_msg)

    async def handle_request(self, request: RPCRequest) -> RPCResponseModel:
        try:
            method = getattr(self, request.cmd)
        except AttributeError:
            raise UnknownRPCCommand(f"Unknown RPC command {request.cmd!r} in request {request!r}.")
        return await method(request)

    async def get_school_to_authority_mapping(self, request: RPCRequest) -> RPCResponseModel:
        return RPCResponseModel(
            result=School2SchoolAuthorityMapping(mapping=self.in_queue.school_authority_mapping)
        )

    async def put_school_to_authority_mapping(self, request: RPCRequest) -> RPCResponseModel:
        obj = School2SchoolAuthorityMapping(**request.school_to_authority_mapping)
        await ConfigurationStorage.save_school2target_mapping(obj)
        # update class attribute inplace
        self.in_queue.school_authority_mapping.clear()
        self.in_queue.school_authority_mapping.update(request.school_to_authority_mapping["mapping"])
        self.logger.info(
            "School2SchoolAuthorityMapping was updated. New mapping: %r",
            self.in_queue.school_authority_mapping,
        )
        return RPCResponseModel(result=obj)

    async def get_queues(self, request: RPCRequest) -> RPCResponseModel:
        return RPCResponseModel(
            result=AllQueues(
                in_queue=self.in_queue.as_queue_model(),
                out_queues=sorted(
                    [q.as_queue_model() for q in self.active_out_queues],
                    key=lambda x: x.name,
                ),
            )
        )

    async def get_queue(self, request: RPCRequest) -> RPCResponseModel:
        for queue in [self.in_queue] + list(self.active_out_queues):
            if queue.name == request.name:
                return RPCResponseModel(result=queue.as_queue_model())
        else:
            raise NoObjectError(key="name", value=request.name)

    async def get_school_authorities(self, request):
        return RPCResponseModel(
            result=sorted(
                [q.school_authority for q in self.out_queues if q.school_authority],
                key=lambda x: x.name,
            )
        )

    async def get_school_authority(self, request: RPCRequest) -> RPCResponseModel:
        for queue in self.out_queues:
            if queue.name == request.name:
                return RPCResponseModel(result=queue.school_authority)
        else:
            raise NoObjectError(key="name", value=request.name)

    async def create_school_authority(self, request: RPCRequest) -> RPCResponseModel:
        school_authority = SchoolAuthorityConfiguration(**request.school_authority)

        # make sure there is no such queue already
        for out_queue in self.out_queues:
            if out_queue.school_authority and out_queue.school_authority.name == school_authority.name:
                raise ObjectExistsError(key="name", value=school_authority.name)

        # create new school_authority and out queue
        self.logger.info(
            "Creating new school authority:\n%s",
            pprint.pformat(school_authority.dict()),
        )
        school_authority.url.rstrip("/")
        out_queue = OutQueue.from_school_authority(school_authority)
        self.out_queues.append(out_queue)
        self.out_queues.sort(key=lambda x: x.name)
        self.logger.info("Created new out queue %r.", out_queue)
        if not self.in_queue.out_queues:
            # This is really weird! It only happens if self.in_queue.out_queues
            # was empty from the start. If an out_queue was created in
            # queue_management.IDConnectorService.manage_queues() from a saved
            # school authority configuration, this does not happen.
            # A CPython optimization for empty lists maybe?
            self.in_queue.out_queues = self.out_queues
        await self.save_school_authority_configuration(out_queue)
        await self.start_out_queue_task(out_queue)
        return RPCResponseModel(result=out_queue.school_authority)

    async def delete_school_authority(self, request: RPCRequest) -> RPCResponseModel:
        for out_queue in self.out_queues:
            if out_queue.name == request.name:
                self.logger.info(
                    "Deleting school authority configuration %r...",
                    out_queue.school_authority.name,
                )
                self.out_queues.remove(out_queue)
                await out_queue.stop_task()
                await out_queue.delete_queue()
                await ConfigurationStorage.delete_school_authority(out_queue.school_authority.name)
                return RPCResponseModel()
        else:
            raise NoObjectError(key="name", value=request.name)

    async def patch_school_authority(self, request: RPCRequest) -> RPCResponseModel:
        name = request.name
        school_authority_doc = SchoolAuthorityConfigurationPatchDocument(**request.school_authority)

        # find and update school_authority_doc and out queue
        for out_queue in self.out_queues:
            if out_queue.school_authority and out_queue.school_authority.name == name:
                self.logger.info(
                    "Updating school authority %r (%r) with:\n%s",
                    out_queue.school_authority.name,
                    out_queue,
                    pprint.pformat(school_authority_doc.dict()),
                )
                await out_queue.stop_task()
                for field in school_authority_doc.fields.keys():
                    value = getattr(school_authority_doc, field)
                    if value is not None:
                        setattr(out_queue.school_authority, field, value)
                self.logger.info("Updated school authority %r.", out_queue.school_authority.name)
                break
        else:
            raise NoObjectError(key="name", value=name)

        await self.save_school_authority_configuration(out_queue)
        await self.start_out_queue_task(out_queue)
        return RPCResponseModel(result=out_queue.school_authority)
