# Like what you see? Join us!
# https://www.univention.com/about-us/careers/vacancies/
#
# Copyright (C) 2021-2023 Univention GmbH
#
# SPDX-License-Identifier: AGPL-3.0-only
#
# https://www.univention.com/
#
# All rights reserved.
#
# The source code of this program is made available under the terms of
# the GNU Affero General Public License v3.0 only (AGPL-3.0-only) as
# published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the AGPL-3.0-only.
#
# In the case you use this program under the terms of the AGPL-3.0-only,
# the program is provided in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/agpl-3.0.txt>.

# convert docbook macros to rst macros.
# Be aware of https://github.com/sphinx-doc/sphinx/issues/3151
# Hence we have normal versions and italics version of substitutions

import re
import sys

if len(sys.argv) < 2:
    print(f"Call as: {sys.argv[0]} <name of file>")
    sys.exit(1)
lines = open(sys.argv[1]).readlines()
for line in lines:
    match = re.match(r'<!ENTITY\s+(\w*)\s+"(.+)"', line)
    if match:
        shortcut = match.group(1)
        shortcut = shortcut.replace("ucs", "")

        longform = match.group(2)
        longform = longform.replace("@", r"\@")

        print(f".. |{shortcut}| replace:: {longform}")
        print(f".. |i{shortcut}| replace:: *{longform}*")

print(
    """
.. |IDC|     replace:: |UAS| ID Connector
.. |iIDC|    replace:: |iUAS| *ID Connector*
.. |IDCS|    replace:: |IDC| Service
.. |iIDCS|   replace:: |iIDC| *Service*
.. |IDCH|    replace:: |IDC| HTTP API
.. |iIDCH|   replace:: |IDC| *HTTP API*
.. |KLV|     replace:: Kelvin
.. |iKLV|    replace:: *Kelvin*
.. |br|      raw:: html

    <br>
"""
)
