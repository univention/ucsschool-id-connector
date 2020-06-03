.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

Changelog
---------

v1.1.0 (2020-06-02)
...................
* The source code that is responsible for replicating users to specific target systems has been moved to plugins.
* The new variable ``postprocessing_plugins`` allows configuring which plugin to use for each school authority configuration.
* In combination the previous two features allow the connector to target a different API for each school authority.
* Update to Python 3.8.

v1.0.0 (2019-11-15)
...................
* Initial release.
