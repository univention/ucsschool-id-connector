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

.. This file is formatted in the spirit of
   https://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. include:: <isonum.txt>


***************************
Example json configurations
***************************


Sending system examples
=======================

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

.. _mapped_udm_properties_json:

Mapped UDM properties
---------------------

.. literalinclude:: ../examples/mapped_udm_properties.json
