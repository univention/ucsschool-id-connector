.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. ID Connector documentation main file, created by

.. include:: univention_rst_macros.txt
.. title:: ID-Connector - Welcome to UCS@School ID Connector Documentation

********************************
|UAS| ID Connector documentation
********************************

.. image:: /images/License-AGPL-v3-orange.*
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0

.. image:: /images/python-3.8-blue.*
    :alt: Python 3.8
    :target: https://www.python.org/downloads/release/python-382/

The |IDC| connects an |UAS| directory
to any number of other |UAS| directories in a 1:n relation.
It's designed to connect state directories with school districts,
but you can also use it in other contexts.
The connection takes place unidirectional.
The connector transfers user data such as user,
school affiliation, class affiliations from a central directory,
for example a country directory,
to district or school directories.

Prerequisite is the |iUAS| |iKLV| API in the school authority environments.
This requires a configuration in advance to create an assignment
*"Which remote instance needs which school users?"*
Then the connector creates, updates, or deletes these users.

.. figure:: images/ucsschool-id-connector_overview_extended.*

   Topology of the |UAS| ID Connector

In this documentation, you learn how to manage an |IDC| setup,
and how to develop plugins for |IDC|.

.. _l10n:

.. tip::

   The |IDC| setup is primarily used in German-speaking countries.
   Hence, you encounter a few German terms in this documentation.

   Sender
      Refers to the sending side of the sync process,
      which in Germany most likely is a state department.

   Traeger
      This is the organization managing schools.
      In the |IDC| context it's the *recipient* of sync data.

.. tip::

   You can use the clipboard icon on the top right of code examples
   to copy the code without Python and Bash prompts:

   .. code-block:: bash

      $ echo "hello world"

   Hover with your mouse over the code to see the icon.

.. Missing elements in the introduction:

   FIXME : Who is the audience?
   FIXME : What know-how is required from the reader to follow along?

.. toctree::
   :caption: Table of contents
   :maxdepth: 2
   :numbered: 3

   admin
   development
   file_locations
   example_json
   HISTORY
   source-docs
   bibliography
