#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO: adapt path of hashbang, when project gets renamed

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
import signal
from typing import List

import aiojobs

from ucsschool_id_connector.config_storage import (
    ConfigurationStorage,
    SchoolAuthorityConfigurationLoadingError,
    SchoolMappingLoadingError,
)
from ucsschool_id_connector.constants import LOG_FILE_PATH_QUEUES, RPC_ADDR, SERVICE_NAME
from ucsschool_id_connector.plugin_loader import load_plugins
from ucsschool_id_connector.plugins import plugin_manager
from ucsschool_id_connector.queues import InQueue, OutQueue, get_out_queue_dirs
from ucsschool_id_connector.rpc import SimpleRPCServer
from ucsschool_id_connector.utils import ConsoleAndFileLogging, get_app_version


class IDConnectorService:
    out_queues: List[OutQueue]
    in_queue: InQueue
    rpc_server: SimpleRPCServer

    def __init__(self):
        self.logger = ConsoleAndFileLogging.get_logger(self.__class__.__name__, LOG_FILE_PATH_QUEUES)

    def handler(self, signum, frame):
        self.should_shutdown = True

    def run(self) -> None:
        self.logger.info("%s %s starting...", SERVICE_NAME, get_app_version())
        self.should_shutdown = False
        signal.signal(signal.SIGINT, self.handler)
        signal.signal(signal.SIGTERM, self.handler)
        asyncio.run(self.manage_queues())
        self.logger.info("%s %s stopped.", SERVICE_NAME, get_app_version())

    async def manage_queues(self) -> None:
        load_plugins()
        try:
            await InQueue.load_school_authority_mapping()
        except SchoolMappingLoadingError as exc:
            self.logger.fatal("Configuration error, aborting: %s", exc)
            await self.shutdown()
            return

        self.logger.info(
            "Loaded school to school authority mapping:\n%s",
            pprint.pformat(InQueue.school_authority_mapping),
        )
        scheduler = await aiojobs.create_scheduler()
        InQueue.scheduler = scheduler
        OutQueue.scheduler = scheduler
        try:
            self.out_queues = [
                OutQueue.from_school_authority(school_authority)
                async for school_authority in ConfigurationStorage.load_school_authorities()
            ]
        except SchoolAuthorityConfigurationLoadingError:
            self.logger.fatal("Configuration error, aborting.")
            await self.shutdown(scheduler)
            return
        self.out_queues.sort(key=lambda x: x.name)
        out_queue_dirs = [q.path for q in self.out_queues]
        abandoned_out_queue_dirs = [
            path.name async for path in get_out_queue_dirs() if path not in out_queue_dirs
        ]
        if abandoned_out_queue_dirs:
            self.logger.warning("Found abandoned out queue directories: %r", abandoned_out_queue_dirs)
        self.in_queue = InQueue(out_queues=self.out_queues)
        if list(self.out_queues):
            self.logger.info("Running initial distribution of in-queue...")
            await self.in_queue.distribute()
        self.logger.info("Starting in-queue background task...")
        await self.in_queue.start_task("distribute_loop", ignore_inactive=True)
        for out_queue in self.out_queues:
            if out_queue.school_authority.active:
                self.logger.info(
                    "Starting out queue background task for school authority %r...",
                    out_queue.school_authority.name,
                )
                await out_queue.start_task("scan")
            else:
                self.logger.info(
                    "Not starting out queue task for deactivated school authority %r.",
                    out_queue.school_authority.name,
                )
        self.logger.info("Starting RPC server task...")
        self.rpc_server = SimpleRPCServer(
            addr=RPC_ADDR, in_queue=self.in_queue, out_queues=self.out_queues
        )
        self.rpc_server.task = await scheduler.spawn(self.rpc_server.simple_rpc_server())
        self.logger.info("Started %d background tasks.", len(scheduler))
        self.logger.info("Sleeping until shutdown is requested (SIGTERM).")
        while not self.should_shutdown:  # sleep until SIGTERM
            await asyncio.sleep(1)
        await self.shutdown(scheduler)

    async def shutdown(self, scheduler: aiojobs.Scheduler = None):
        if scheduler:
            self.logger.info("Shutting down all running tasks...")
            await scheduler.close()
        self.logger.info("Closing cache and DB connections...")
        # nothing to do at the moment
        self.logger.info("Shutting down all outgoing connections...")
        await asyncio.gather(*plugin_manager.hook.shutdown())
        await asyncio.sleep(0.25)  # allow aiohttp SSL connections to close gracefully


def main():
    service = IDConnectorService()  # nosec
    service.run()
