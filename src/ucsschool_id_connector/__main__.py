#!/usr/bin/python3
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

"""
Command line utility.

Extend the choices list of the "command" argument to dispatch more commands.
"""

import asyncio
import logging
import sys

import click

from .constants import LOG_FILE_PATH_MIGRATION
from .migrations import ConversionError, migrate_school_authority_configuration_to_plugins
from .utils import ConsoleAndFileLogging, get_app_version


@click.command()
@click.argument(
    "command",
    type=click.Choice(["migrate-school-authority-configurations", "version"]),
)
def cli(command: str) -> None:
    if command == "migrate-school-authority-configurations":
        logger = ConsoleAndFileLogging.get_logger("ucsschool_id_connector", LOG_FILE_PATH_MIGRATION)
        logger.addHandler(logging.StreamHandler(stream=sys.stdout))
        logger.info("Logging to %r.", str(LOG_FILE_PATH_MIGRATION))
        try:
            asyncio.run(migrate_school_authority_configuration_to_plugins())
        except ConversionError as exc:
            click.echo(str(exc))
            sys.exit(1)
    if command == "version":
        click.echo(get_app_version())


if __name__ == "__main__":
    cli()
