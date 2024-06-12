.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

*********
Changelog
*********

.. _3.0.0:

v3.0.0 (2024-05-23)
===================

* Breaking: The ID Connector now trusts all certificates, on the UCS system. If your ID Connector connects to any recipient servers that use a private CA, you need to add that CA to the UCS system before you update (Issue #58).
* Breaking: Cron job for ``listener_trash_cleaner`` was moved from the container to the host (Bug #54640).
* Breaking: The ID Connector image is now build based on the UCS base image and not Alpine anymore (Issue #15).
* Breaking: The ID Connector is now using Python 3.11 and not Python 3.8 (Issue #66).
* Chore: Dependencies have been updated (Issue #68).
* Fixed: Updating or re-adding previously deleted school authority configuration through the web API, did not take affect until the app had been restarted. This has been fixed and a restart is not necessary anymore (Issue #70).

.. _2.3.3:

v2.3.3 (2024-01-11)
===================

* The python package tenacity has been added as additional dependency to properly support the ID-Broker plugin (Issue #101).

.. _2.3.2:

v2.3.2 (2024-01-08)
===================

* The scripts to schedule users, groups and schools have been improved to have a help message (Issue #47).

.. _2.3.1:

v2.3.1 (2023-11-30)
===================

* A new ``schedule_group`` command has been added. It can be used to force a group to be synced again (Issue #41).
* A new ``schedule_school`` command has been added. It can be used to force a school to be synced again (Issue #41).
* The ID Connector API patch endpoint for school authorities was fixed (Issue #44).

.. _2.3.0:

v2.3.0 (2023-11-30)
===================

* The rotation of log files is now managed by the UCS host systems ``logrotate``.
  This is also fixing a bug that could lead to missing log entries. (:uv:bug:`55983`).

.. _2.2.8:

v2.2.8 (2023-08-21)
===================

* ID Connector Kelvin plugin compares OU names case insensitive (:uv:bug:`55344`).
* Upgrade ``Pydantic``, improve ``ListenerFileAttributeError`` exceptions (:uv:bug:`56399`).
* The automatic clean up of the ID Connector's ``trash`` directory now works as intended (:uv:bug:`56235`).
  The following issues were fixed:

  - The ``listener_trash_cleaner`` file is now executable.
  - The ``cron daemon`` within the Docker-Container runs on startup of the container.

.. _2.2.7:

v2.2.7 (2023-06-22)
===================

* Updated upstream dependencies. A security vulnerability in ``starlette`` (:uv:cve:`2023-30798`) was fixed (:uv:bug:`56265`).

.. _2.2.6:

v2.2.6 (2023-06-14)
===================

* The ID Connector can now be configured to automatically clean up its ``trash`` directory periodically (:uv:bug:`53048`).
  Two new app settings where created:

  - ``trash_delete_state`` determines if the clean up should be run periodically,
  - ``trash_delete_offset`` determines after how many days old listener files are be cleaned up.

.. _2.2.5:

v2.2.5 (2023-03-29)
===================

* Boolean attributes are now synced correctly (:uv:bug:`54307`).

  .. note::

     The format of objects which are written by the listener and read by the ID
     Connector plugins changed from version ``2.2.4`` and ``2.2.5`` (cf.
     :uv:bug:`54773`). It now has the format of the UDM Rest API objects (e.g.
     users and groups). Customized plugins might have to be adapted.

.. _2.2.4:

v2.2.4 (2022-08-25)
===================

* Users with multiple schools are now updated correctly if the Kelvin REST API is installed in version ``1.5.4`` or above on the school authority side.

* The permissions of the school authority configuration files was fixed.

* Kelvin REST API versions up to ``1.7.0`` are now supported.

  .. warning::

     Kelvin REST API version ``1.7.0`` and above will break ID Connector versions below ``2.2.4``.

* Remote school (OU) names are now compared case insensitively.

.. _2.2.2:

v2.2.2 (2022-03-03)
===================

* The ID Broker plugin was removed from the app and can be installed separately by a Debian package.
* The ID Broker partial group sync plugin now safely handles group names with hyphen).
* Fixed users with multiple schools being created in alphabetical first, instead of same as in source domain.

.. _2.2.0:

v2.2.0 (2022-01-04)
===================

* A new plugin was added to sync all user data to the ID Broker.

* The ID Connector can now also be installed on DC Backups.

* The Kelvin plugin can now be imported by other plugins, so they can subclass it.

* The synchronization of the ``birthday`` and ``userexpiry`` (in Kelvin ``expiration_date``) attributes was fixed.
  The Kelvin REST API on the school authority side must be of version ``1.5.1`` or above!

.. _2.1.1:

v2.1.1 (2021-10-25)
===================

* The log level for messages written to :file:`/var/log/univention/ucsschool-id-connector/*.log` is now configurable.
  Valid values are ``DEBUG``, ``INFO``, ``WARNING`` and ``ERROR``. Defaults to ``INFO``.

.. _2.1.0:

v2.1.0 (2021-10-11)
===================

* Update the integrated kelvin rest client to version ``1.5.0`` to work with Kelvin ``1.5.0``
* Include kelvin plugin derivative for partial group sync.

.. _2.0.1:

v2.0.1 (2021-03-04)
===================

* The transfer of Kerberos key hashes has been fixed.

.. _2.0.0:

v2.0.0 (2020-11-10)
===================

* Add Kelvin API plugin, which can be used with the ID Connector.
  The receiving side is required to have installed at least version ``1.2.0`` of the Kelvin API.

* The BB API plugin has been removed.

.. _1.1.0:

v1.1.0 (2020-06-02)
===================

* The source code that is responsible for replicating users to specific target systems has been moved to plugins.
* The new variable ``plugins`` allows configuring which plugin to use for each school authority configuration.
* In combination the previous two features allow the connector to target a different API for each school authority.
* Update to Python 3.8.

.. _1.0.0:

v1.0.0 (2019-11-15)
===================

* Initial release.
