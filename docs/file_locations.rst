.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

File locations
==============

This section lists relevant directories and files. Configuration file *must not* be edited by hand.
All configuration is done either through the *app settings* in the UCS app center or through the
*UCS\@school ID Connector HTTP API*.

Nothing needs to be backed up and restored before and after an app update,
because all important data is persisted in files on volumes
mounted from the UCS host into the docker container.

Log files
---------

``/var/log/univention/ucsschool-id-connector`` is a volume mounted into the docker container,
so it can be accessed from the host.

The directory contains:

* ``http.log``: log of the HTTP-API (both ASGI server and API application)
* ``queues.log``: log of the queue management daemon
* Old versions of above log files with timestamps appended to the file name.
  Log file rotation happens on Mondays and 15 copies are kept.

Log output can also be seen running::

    $ docker logs <container name>

School authority configuration files
------------------------------------

The configuration of the replication targets (*school authorities / Schulträger*) is stored
in one JSON file per configured school authority under
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/school_authorities``.
The JSON configuration files must not be created by hand.
The HTTP-API should be used for that instead.

Each school authority configuration has a queue associated.

Queue files
-----------

The LDAP listener process on the UCS host creates a JSON file
for each creation/modification/move/deletion of a user object.
Those JSON files are written to
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/listener``.
That is the directory of the *in queue*.

The process handling the *in queue* copies files from there to a directory
for each school authority that it can associate with the user account in the file.
Each *out queue* handles a directory below
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues``.

When a school authority configuration is deleted, its associated queue directory is moved to
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues_trash``.

Token signature key
-------------------

The key with which the JWTs are signed is in the file
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret``.
The file is created by the apps join script (see *Install* above).

SSL certificates for Kelvin client plugin
-----------------------------------------

The plugin that connects to the Kelvin API on the school authority side looks for and stores
SSL certificates as
``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/ssl_certs/HOSTNAME``.
In case the certificate cannot be downloaded automatically, it can be saved there manually.

Volumes
-------
The following directories are mounted from the host into the container:

* ``/var/lib/univention-appcenter/listener``
* ``/var/log/univention/ucsschool-id-connector``
