.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. This file is formatted in the spirit of
   https://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. include:: <isonum.txt>
.. include:: univention_rst_macros.txt

***************************
Example json configurations
***************************

This section provides some example configurations.

Sending system examples
=======================

Here you find example configurations for the sending system of an |IDC| setup.

.. _school-authority-mapping:

School authority configuration
------------------------------

.. literalinclude:: ../examples/school_authority_kelvin.json


.. _school-to-authority-mapping:

School to authority mapping example
-----------------------------------

.. literalinclude:: ../examples/mapping.json


.. _role-specific-kelvin-plugin-mapping:

Role specific Kelvin plugin mapping
-----------------------------------

.. literalinclude:: ../examples/school_authority_role_specific_kelvin_mapping.json


.. _partial-groupsync:

Partial group sync
------------------

This uses the ``kelvin-partial-group-sync`` plugin instead of the ``kelvin`` plugin in the
`Role specific Kelvin plugin mapping`_.

.. literalinclude:: ../examples/school_authority_kelvin_partial_group_sync.json


Receiving system examples
=========================

Here you find example configurations for the receiving system of an |IDC| setup.

.. _mapped-udm-properties-json:

Mapped UDM properties
---------------------

.. literalinclude:: ../examples/mapped_udm_properties.json
