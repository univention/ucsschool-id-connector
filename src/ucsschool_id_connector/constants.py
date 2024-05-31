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

import os
import re
from pathlib import Path

APP_ID = "ucsschool-id-connector"
SERVICE_NAME = "IDConnectorService"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_SRC_PATH = Path(f"/{APP_ID}/src")
APPCENTER_LISTENER_PATH = Path("/var/lib/univention-appcenter/listener", APP_ID)
APP_CONFIG_BASE_PATH = Path(APP_BASE_PATH, "conf")
APP_DATA_BASE_PATH = Path(APP_BASE_PATH, "data")
IN_QUEUE_DIR = Path(APP_DATA_BASE_PATH, "listener")
OLD_DATA_DB_PATH = Path(APP_DATA_BASE_PATH, "old_data_db")
OUT_QUEUE_TOP_DIR = Path(APP_DATA_BASE_PATH, "out_queues")
OUT_QUEUE_TRASH_DIR = Path(APP_DATA_BASE_PATH, "out_queues_trash")
SCHOOL_AUTHORITIES_CONFIG_PATH = Path(APP_CONFIG_BASE_PATH, "school_authorities")
SCHOOLS_TO_AUTHORITIES_MAPPING_PATH = Path(APP_CONFIG_BASE_PATH, "schools_authorities_mapping.json")
AUTO_CHECK_INTERVAL = 60
HTTP_REQUEST_TIMEOUT = 20.0
LOG_DIR = Path(os.environ.get("LOG_DIR", f"/var/log/univention/{APP_ID}"))
LOG_FILE_PATH_HTTP = Path(LOG_DIR, "http.log")
LOG_FILE_PATH_MIGRATION = Path(LOG_DIR, "migration.log")
LOG_FILE_PATH_QUEUES = Path(LOG_DIR, "queues.log")
LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_ENTRY_DEBUG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
LOG_ENTRY_CMDLINE_FORMAT = "%(log_color)s%(levelname)-5s: %(message)s"

RPC_ADDR = "tcp://127.0.0.1:5678"
URL_PREFIX = f"/{APP_ID}/api/v1"
UCR_DB_FILE = "/etc/univention/base.conf"
UCR_REGEX = re.compile(r"^(?P<ucr>.+?): (?P<value>.*)$")
TOKEN_SIGN_SECRET_FILE = Path(APP_CONFIG_BASE_PATH, "tokens.secret")  # nosec
TOKEN_HASH_ALGORITHM = "HS256"  # nosec
TOKEN_URL = f"/{APP_ID}/api/token"
UCRV_LOG_LEVEL = (f"{APP_ID}/log_level", "INFO")
UCRV_SOURCE_UID = (f"{APP_ID}/source_uid", "TESTID")
UCRV_TOKEN_TTL = (f"{APP_ID}/access_tokel_ttl", 60)
ADMIN_GROUP_NAME = f"{APP_ID}-admins"
API_SCHOOL_CACHE_TTL = 600
API_COMMUNICATION_ERROR_WAIT = 600
SOURCE_UID = "TESTID"
MACHINE_PASSWORD_FILE = "/etc/machine.secret"  # nosec
HTTP_CLIENT_TIMEOUT = 60
HISTORY_FILE = "HISTORY.html"
README_FILE = "README.html"
RPC_CLIENT_TIMEOUT = 5000  # ms
PLUGIN_NAMESPACE = "ucsschool_id_connector"
PLUGIN_PACKAGE_DIRS = (
    APP_SRC_PATH / "plugins/packages",
    APP_CONFIG_BASE_PATH / "plugins/packages",
)
PLUGIN_DIRS = (
    APP_SRC_PATH / "plugins/plugins",
    APP_CONFIG_BASE_PATH / "plugins/plugins",
)
UCR_CONTAINER_CLASS = ("ucsschool_ldap_default_container_class", "klassen")
UCR_CONTAINER_PUPILS = ("ucsschool_ldap_default_container_pupils", "schueler")
UCR_CONTAINER_TEACHERS = ("ucsschool_ldap_default_container_teachers", "lehrer")
UCR_CONTAINER_TEACHERS_AND_STAFF = (
    "ucsschool_ldap_default_container_teachers_and_staff",
    "lehrer und mitarbeiter",
)
UCR_GROUP_PREFIX_STUDENTS = ("ucsschool_ldap_default_groupprefix_pupils", "schueler-")
UCR_GROUP_PREFIX_TEACHERS = ("ucsschool_ldap_default_groupprefix_teachers", "lehrer-")
