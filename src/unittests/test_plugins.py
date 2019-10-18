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

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

import id_sync.constants
import id_sync.plugin_loader
import id_sync.plugins


class DummyPluginSpec:
    @id_sync.plugins.hook_spec(firstresult=True)
    def dummy_func(self, arg1, arg2):
        """An example hook."""


@pytest.fixture
def example_plugin(random_name):
    # replace /var/lib/univention-appcenter/apps/id-sync with path below /tmp
    # and /id-sync/src with ../..
    tmp_dir = Path("/tmp/", random_name())
    default_package_dir = Path(__file__).parent.parent / "plugins/packages"
    custom_package_base_dir = tmp_dir / "plugins/packages"
    custom_package_base_dir.mkdir(parents=True)
    mock_package_dirs = (default_package_dir, custom_package_base_dir)
    default_plugin_dir = Path(__file__).parent.parent / "plugins/plugins"
    custom_plugin_dir = tmp_dir / "plugins/plugins"
    custom_plugin_dir.mkdir(parents=True)
    mock_plugin_dirs = (default_plugin_dir, custom_plugin_dir)

    id_sync.plugins.plugin_manager.add_hookspecs(DummyPluginSpec)
    custom_package_name = random_name(ints=False)
    custom_package_dir = custom_package_base_dir / custom_package_name
    custom_package_dir.mkdir(parents=True)
    custom_module_name = random_name(ints=False)
    custom_module_path = custom_package_dir / f"{custom_module_name}.py"
    with open(custom_module_path, "w") as fp:
        fp.write(CUSTOM_TEST_MODULE_IN_PACKAGE)
    custom_plugin_name = random_name(ints=False)
    custom_plugin_path = custom_plugin_dir / f"{custom_plugin_name}.py"
    with open(custom_plugin_path, "w") as fp:
        fp.write(
            CUSTOM_DUMMY_PLUGIN.format(
                module_name=custom_module_name, package_name=custom_package_name
            )
        )
    default_plugin_name = random_name(ints=False)
    default_plugin_path = default_plugin_dir / f"{default_plugin_name}.py"
    with open(default_plugin_path, "w") as fp:
        fp.write(DEFAULT_DUMMY_PLUGIN)

    yield mock_package_dirs, mock_plugin_dirs

    id_sync.plugins.plugin_manager.unregister(DummyPluginSpec)
    shutil.rmtree(tmp_dir)
    default_plugin_path.unlink()
    for path in (default_plugin_dir / "__pycache__").glob(
        f"{default_plugin_name}.*.pyc"
    ):
        path.unlink()
    try:
        (default_plugin_dir / "__pycache__").rmdir()
    except OSError:
        pass


def test_load_plugins(example_plugin, random_int):
    mock_package_dirs, mock_plugin_dirs = example_plugin
    with patch.object(
        id_sync.plugin_loader, "PLUGIN_PACKAGE_DIRS", mock_package_dirs
    ), patch.object(id_sync.plugin_loader, "PLUGIN_DIRS", mock_plugin_dirs):
        id_sync.plugin_loader.load_plugins()
    arg1 = random_int()
    arg2 = random_int()
    res = id_sync.plugins.plugin_manager.hook.dummy_func(arg1=arg1, arg2=arg2)
    assert res == arg1 + arg2


DEFAULT_DUMMY_PLUGIN = """
from id_sync.utils import ConsoleAndFileLogging
from id_sync.plugins import hook_impl, plugin_manager
logger = ConsoleAndFileLogging.get_logger(__name__)
class DefaultDummyPlugin:
    @hook_impl
    def dummy_func(self, arg1, arg2):
        logger.info("Running DefaultDummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
        return arg1 - arg2
plugin_manager.register(DefaultDummyPlugin())
"""

CUSTOM_DUMMY_PLUGIN = """
from id_sync.utils import ConsoleAndFileLogging
from id_sync.plugins import hook_impl, plugin_manager
from {package_name}.{module_name} import ExampleTestClass
logger = ConsoleAndFileLogging.get_logger(__name__)
class DummyPlugin:
    @hook_impl
    def dummy_func(self, arg1, arg2):
        logger.info("Running DummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
        example_obj = ExampleTestClass()
        res = example_obj.add(arg1, arg2)
        assert res == arg1 + arg2
        return res
plugin_manager.register(DummyPlugin())
"""

CUSTOM_TEST_MODULE_IN_PACKAGE = """
from id_sync.utils import ConsoleAndFileLogging
logger = ConsoleAndFileLogging.get_logger(__name__)
class ExampleTestClass:
    def add(self, arg1, arg2):
        logger.info("Running ExampleTestClass.example_func() with arg1=%r arg2=%r.", arg1, arg2)
        return arg1 + arg2
"""