.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

File locations
==============

This section lists relevant directories and files.
**Don't** edit configuration files by hand.
*App settings* in the UCS App Center
or the *UCS\@school ID Connector HTTP API* take care of all configuration.

All important data persists in files on volumes
mounted from the UCS host into the Docker container.
Therefore, there is no need for distinct backup before an update
and a restore afterwards.

Log files
---------

The directory :file:`/var/log/univention/ucsschool-id-connector`
is a volume mounted into the Docker container,
so that you can access it from the host.

The directory contains the following files:

* :file:`http.log`: log file of the HTTP-API, both ASGI server and API application.
* :file:`queues.log`: log file of the queue management daemon.
* Previous versions of before mentioned log files with timestamps appended to the filename.

The system's :program:`logrotate` settings control log file rotation.
For example, to change the rotation cycle to daily for :file:`queues.log`,
use the following command:

.. code-block:: bash

    $ ucr set logrotate/ucsschool-id-connector/queues/rotate=daily

.. seealso::

   See :ref:`computers-logging-retrieval-of-system-messages-and-system-status` in :cite:t:`uv-manual`.

To view log file output, run the following command:

.. code-block:: bash

    $ docker logs <container name>

School authority configuration files
------------------------------------

The configuration of the replication targets, such as *school authorities / Schulträger*,
locates in one JSON file per configured school authority in the directory
:file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/school_authorities`.
Don't create the JSON configuration by hand.
Use the *UCS\@school ID Connector HTTP API* instead.

Token signature key
-------------------

The key for signing the JWTs locates in the file
:file:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret`.
The app join script creates this file.
For more information, see :ref:`admin-install`.

SSL certificates for Kelvin client plugin
-----------------------------------------

The plugin that connects to the Kelvin API on the school authority side looks for and stores
SSL certificates as file
:samp:`/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/ssl_certs/{HOSTNAME}`.
If the *Kelvin client plugin* can't download the certificate automatically,
you can manually save it to the preceding location.

Volumes
-------

The Docker container mounts the following host directories as volumes:

* :file:`/var/lib/univention-appcenter/listener`
* :file:`/var/log/univention/ucsschool-id-connector`
