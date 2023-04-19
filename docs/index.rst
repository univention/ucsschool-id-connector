.. Like what you see? Join us!
.. https://www.univention.com/about-us/careers/vacancies/
..
.. Copyright (C) 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only
..
.. https://www.univention.com/
..
.. All rights reserved.
..
.. The source code of this program is made available under the terms of
.. the GNU Affero General Public License v3.0 only (AGPL-3.0-only) as
.. published by the Free Software Foundation.
..
.. Binary versions of this program provided by Univention to you as
.. well as other copyrighted, protected or trademarked materials like
.. Logos, graphics, fonts, specific documentations and configurations,
.. cryptographic keys etc. are subject to a license agreement between
.. you and Univention and not subject to the AGPL-3.0-only.
..
.. In the case you use this program under the terms of the AGPL-3.0-only,
.. the program is provided in the hope that it will be useful, but
.. WITHOUT ANY WARRANTY; without even the implied warranty of
.. MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
.. Affero General Public License for more details.
..
.. You should have received a copy of the GNU Affero General Public
.. License with the Debian GNU/Linux or Univention distribution in file
.. /usr/share/common-licenses/AGPL-3; if not, see
.. <https://www.gnu.org/licenses/agpl-3.0.txt>.

.. ID Connector documentation main file, created by
   sphinx-quickstart on Tue Nov  2 14:56:07 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root toctree directive.
.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt
.. title:: ID-Connector - Welcome to UCS@School ID Connector Documentation

****************************************************
Welcome to |UAS| ID Connector's documentation!
****************************************************


.. image:: /images/License-AGPL-v3-orange.*
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0

.. image:: /images/python-3.8-blue.*
    :alt: Python 3.8
    :target: https://www.python.org/downloads/release/python-382/


The |IDC| connects an |UAS| directory to any number of other |UAS| directories (1:n).
It is designed to connect state directories with school districts,
but can also be used in other contexts.
The connection takes place unidirectional: user data (user, school affiliation, class affiliations)
is transferred from a central directory (e.g. country directory) to district or school directories.
Prerequisite is the use of the |iUAS| |iKLV| API on the school authorities.
For this a configuration is necessary in advance to create an assignment
"Which school users should be transferred to which remote instance?"
Then these users are created, updated and deleted.

.. figure:: images/ucsschool-id-connector_overview_extended.*
   :width: 600
   :align: center

In this documentation, you will learn how to administer an |IDC| setup,
and we hope to teach you how to develop plugins for |IDC| as well.

.. _l10n:

.. note::

   At the moment, the |IDC| setup is only used in German-speaking countries. Hence, you will
   encounter a few German terms in this documentation.

   Sender
      An easy one to guess - it actually refers to the sending side of the sync process,
      which in Germany most likely is a state department.

   Traeger
      This is the organization managing schools. In the |IDC| context it can be thought
      of as the *recipient* of sync data.

.. note::

   You can use the clipboard icon on the top right of code examples
   to easily copy the code without python and bash prompts:

   .. code-block:: bash

       $ echo "hello world"

   (Hover with your mouse over the code to see the icon)

Contents
========

.. toctree::
   :maxdepth: 4
   :numbered: 3

   admin
   development
   file_locations
   example_json
   HISTORY
   bibliography


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
