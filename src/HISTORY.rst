.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

Changelog
---------

**v2.2.4 (2022-08-25)**

* Kelvin REST API versions up to ``1.7.0`` are now supported.
* Remote school (OU) names are now compared case sensitively.

**v2.2.3 (2022-04-11)**

* Users with multiple schools are now updated correctly if the Kelvin REST API is installed in version ``1.5.4`` or above on the school authority side.
* The permissions of the school authority configuration files was fixed.

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
