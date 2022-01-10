.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

Changelog
---------

v2.2.0 (2022-01-04)
...................

* A new plugin was added to sync all user data to the ID-Broker.
* The ID Connector can now also be installed on DC Backups.

v2.1.1 (2021-10-25)
...................

* The log level for messages written to ``/var/log/univention/ucsschool-id-connector/*.log`` is now configurable. Valid values are ``DEBUG``, ``INFO``, ``WARNING`` and ``ERROR``. Defaults to ``INFO``.

v2.1.0 (2021-10-11)
...................
* Update the integrated kelvin rest client to version ``1.5.0`` to work with Kelvin ``1.5.0``
* Include kelvin plugin derivate for partial group sync

v2.0.1 (2021-03-04)
...................
* The transfer of Kerberos key hashes has been fixed.

v2.0.0 (2020-11-10)
...................
* Add Kelvin API plugin, which can be used with the ID Connector. The receiving side is required to have installed at least version ``1.2.0`` of the Kelvin API.
* The BB API plugin has been removed.

v1.1.0 (2020-06-02)
...................
* The source code that is responsible for replicating users to specific target systems has been moved to plugins.
* The new variable ``plugins`` allows configuring which plugin to use for each school authority configuration.
* In combination the previous two features allow the connector to target a different API for each school authority.
* Update to Python 3.8.

v1.0.0 (2019-11-15)
...................
* Initial release.
