# SPDX-FileCopyrightText: 2021-2023 Univention GmbH
#
# SPDX-License-Identifier: AGPL-3.0-only

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
