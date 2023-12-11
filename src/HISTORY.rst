.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

Changelog
---------

**v2.3.1 (2023-11-30)**

* A new ``schedule_group`` command has been added. It can be used to force a group to be synced again (Issue #41).
* A new ``schedule_school`` command has been added. It can be used to force a school to be synced again (Issue #41).
* The ID Connector API patch endpoint for school authorities was fixed (Issue #44).

**v2.3.0 (2023-11-30)**

* The rotation of log files is now managed by the UCS host systems ``logrotate``. This is also fixing a bug that could lead to missing log entries. (Bug #55983).

**v2.2.8 (2023-08-21)**

* ID Connector Kelvin plugin compares OU names case insensitive (Bug #55344).
* Upgrade ``Pydantic``, improve ``ListenerFileAttributeError`` exceptions (Bug #56399).
* The automatic clean up of the ID Connector's ``trash`` directory now works as intended (Bug #56235).
  The following issues were fixed:

  - The ``listener_trash_cleaner`` file is now executable.
  - The ``cron daemon`` within the Docker-Container runs on startup of the container.


**v2.2.7 (2023-06-22)**

* Updated upstream dependencies. A security vulnerability in ``starlette`` (CVE-2023-30798) was fixed (Bug #56265).

**v2.2.6 (2023-06-14)**

* The ID Connector can now be configured to automatically clean up its ``trash`` directory periodically (Bug #53048).
  Two new app settings where created:

  - ``trash_delete_state`` determines if the clean up should be run periodically,
  - ``trash_delete_offset`` determines after how many days old listener files are be cleaned up.

**v2.2.5 (2023-03-29)**

* Boolean attributes are now synced correctly (Bug #54307). **Info**: The format of objects which are written by the listener and read by the ID Connector plugins changed from version ``2.2.4`` and ``2.2.5`` (cf. Bug #54773). It now has the format of the UDM Rest API objects (e.g. users and groups). Customized plugins might have to be adapted.

**v2.2.4 (2022-08-25)**

* Users with multiple schools are now updated correctly if the Kelvin REST API is installed in version ``1.5.4`` or above on the school authority side.
* The permissions of the school authority configuration files was fixed.
* Kelvin REST API versions up to ``1.7.0`` are now supported. **Warning**: Kelvin REST API version ``1.7.0`` and above will break ID Connector versions below ``2.2.4``.
* Remote school (OU) names are now compared case insensitively.


**v2.2.2 (2022-03-03)**

* The ID Broker plugin was removed from the app and can be installed separately by a Debian package.
* The ID Broker partial group sync plugin now safely handles group names with hyphen).
* Fixed users with multiple schools being created in alphabetical first, instead of same as in source domain.


**v2.2.0 (2022-01-04)**

* A new plugin was added to sync all user data to the ID Broker.
* The ID Connector can now also be installed on DC Backups.
* The Kelvin plugin can now be imported by other plugins, so they can subclass it.
* The synchronization of the ``birthday`` and ``userexpiry`` (in Kelvin ``expiration_date``) attributes was fixed. The Kelvin REST API on the school authority side must be of version ``1.5.1`` or above!


**v2.1.1 (2021-10-25)**

* The log level for messages written to ``/var/log/univention/ucsschool-id-connector/*.log`` is now configurable. Valid values are ``DEBUG``, ``INFO``, ``WARNING`` and ``ERROR``. Defaults to ``INFO``.


**v2.1.0 (2021-10-11)**

* Update the integrated kelvin rest client to version ``1.5.0`` to work with Kelvin ``1.5.0``
* Include kelvin plugin derivative for partial group sync

**v2.0.1 (2021-03-04)**

* The transfer of Kerberos key hashes has been fixed.

**v2.0.0 (2020-11-10)**

* Add Kelvin API plugin, which can be used with the ID Connector. The receiving side is required to have installed at least version ``1.2.0`` of the Kelvin API.
* The BB API plugin has been removed.


**v1.1.0 (2020-06-02)**

* The source code that is responsible for replicating users to specific target systems has been moved to plugins.
* The new variable ``plugins`` allows configuring which plugin to use for each school authority configuration.
* In combination the previous two features allow the connector to target a different API for each school authority.
* Update to Python 3.8.

**v1.0.0 (2019-11-15)**

* Initial release.
