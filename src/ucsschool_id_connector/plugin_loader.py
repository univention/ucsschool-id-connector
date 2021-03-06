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

import importlib
import os
import sys
from typing import Iterator, cast

from ucsschool_id_connector.constants import PLUGIN_DIRS, PLUGIN_PACKAGE_DIRS
from ucsschool_id_connector.plugins import plugin_manager
from ucsschool_id_connector.utils import ConsoleAndFileLogging

__plugins_loaded = False


def load_plugins() -> None:  # noqa: C901
    global __plugins_loaded
    if __plugins_loaded:
        return
    logger = ConsoleAndFileLogging.get_logger(__name__)
    for package_dir in PLUGIN_PACKAGE_DIRS:
        logger.debug("Adding directory to Python path: '%s'...", package_dir)
        if not package_dir.exists():  # pragma: no cover
            package_dir.mkdir(mode=0o755, parents=True)
            with (package_dir / "README.txt").open("w") as fp:
                fp.write("This directory will be added to the PYTHONPATH / sys.path.\n")
        if package_dir not in sys.path:
            sys.path.append(str(package_dir))
    for plugin_dir in PLUGIN_DIRS:
        logger.debug("Looking for plugins in '%s'...", plugin_dir)
        if not plugin_dir.exists():  # pragma: no cover
            plugin_dir.mkdir(mode=0o755, parents=True)
            with (plugin_dir / "README.txt").open("w") as fp:
                fp.write("This directory will be searched for Python modules with plugins.\n")
        with cast(Iterator[os.DirEntry], os.scandir(plugin_dir)) as dir_entries:
            for entry in dir_entries:
                if entry.is_file() and entry.name.lower().endswith(".py"):
                    module_name = entry.name[:-3]
                    logger.debug("Loading module %r in %r...", module_name, entry.path)
                    spec = importlib.util.spec_from_file_location(module_name, entry.path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

    logger.info(
        "Known hooks: %r",
        [h for h in dir(plugin_manager.hook) if not h.startswith("_")],
    )
    plugin_info = {}
    for plugin in plugin_manager.get_plugins():
        plugin_info[f"{plugin.__module__}.{plugin.__class__.__name__}"] = sorted(
            h.name for h in plugin_manager.get_hookcallers(plugin)
        )
    logger.info("Loaded plugins:")
    for plugin_name in sorted(plugin_info.keys()):
        logger.info("    %r: %r", plugin_name, plugin_info[plugin_name])

    __plugins_loaded = True
