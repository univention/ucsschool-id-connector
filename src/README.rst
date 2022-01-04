UCS@school ID Connector
=======================

|python| |license|

.. This file can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/readme
.. The changelog can be read on the installed system at https://FQDN/ucsschool-id-connector/api/v1/history

Introduction
------------

The *UCS\@school ID Connector* replication system is composed of three components:

* A process on the data source UCS server, receiving user creation/modification/deletion events from the LDAP server and relaying them to multiple recipients via HTTP. Henceforth called the *UCS\@school ID Connector service*.
* A process on the data source UCS server to monitor and configure the UCS\@school ID Connector service, henceforth called the *UCS\@school ID Connector HTTP API*.
* Multiple recipients of the directory data relayed by the *UCS\@school ID Connector service*. They run a HTTP-API service, that the *UCS\@school ID Connector service* pushes updates to.

The changelog ist in the `HISTORY <history>`_ file.

Architectural overview
^^^^^^^^^^^^^^^^^^^^^^

|diagram_overview|


Installation
------------

On the server system
^^^^^^^^^^^^^^^^^^^^

The app is  available in the appcenter. Installation::

    $ univention-app install ucsschool-id-connector

The join script ``50ucsschool-id-connector.inst`` must run and create:

* the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret`` containing the key with which JWT tokens are signed.
* the group ``ucsschool-id-connector-admins`` (with DN ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``) whos members are allowed to access the HTTP-API.

If they didn't get created, run::

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst


On the target systems
^^^^^^^^^^^^^^^^^^^^^

A HTTP-API is required for the *UCS\@school ID Connector* app to be able to create/modify/delete users on the target systems. Currently only the Kelvin API is supported. Instructions for installation and configuration can be found in a later section.


Update
------

Updates are installed in one of the two usual UCS ways. Either via UMC or on the command line::

    $ univention-upgrade
    $ univention-app upgrade ucsschool-id-connector


Starting / Stopping services
----------------------------

Both services (*UCS\@school ID Connector service* and *UCS\@school ID Connector HTTP API*) run in a Docker container. The container can be started/stopped by using the regular service facility of the host system::

    $ service docker-app-ucsschool-id-connector start
    $ service docker-app-ucsschool-id-connector status
    $ service docker-app-ucsschool-id-connector stop

To restart individual services, init scripts *inside* the Docker container can be used. The ``univention-app`` program has a command that makes it easy to execute commands *inside* the Docker container::

    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector restart  # UCS@school ID Connector service
    $ univention-app shell ucsschool-id-connector /etc/init.d/ucsschool-id-connector-rest-api start # UCS@school ID Connector HTTP API


Configuration
-------------
The school authorities configuration must be done through the *UCS\@school ID Connector HTTP API*. Do not edit configuration files directly.

* The UDM ``ucsschoolRecordUID`` property (a.k.a. UCS\@school ``record_uid`` property) should be synced to a UCS\@school system as ``record_uid``.
* The UDM ``ucsschoolSourceUID`` property (a.k.a. UCS\@school ``source_uid`` property) should be synced to a UCS\@school system as ``source_uid``.
* The *virtual* (special handling by the *UCS\@school ID Connector* app) ``roles`` property should be synced as ``roles``::

    {
        "plugin_configs": {
            "kelvin": {
                "mapping": {
                    "users": {
                        "ucsschoolRecordUID": "record_uid",
                        "ucsschoolSourceUID": "source_uid",
                        "roles": "roles"
                    }
                }
            }
        }
    }

See ``examples/school_authority_kelvin.json`` for an example.

Further information on the configuration of some select plugins can be found further down.


UCS\@school ID Connector HTTP API
---------------------------------

A HTTP-API of the *UCS\@school ID Connector* app offers two resources:

* *queues*: monitoring of queues
* *school_authorities*: configuration of school authorities

Two websites exist, that allow to interactively discover the API. They can be visited with a browser at the URLS:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: https://FQDN/ucsschool-id-connector/api/v1/docs
* `ReDoc <https://github.com/Rebilly/ReDoc>`_: https://FQDN/ucsschool-id-connector/api/v1/redoc

A `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_ can be downloaded from https://FQDN/ucsschool-id-connector/api/v1/openapi.json

The Swagger UI page is especially helpful as it allows to send queries directly from the browser and displays equivalent ``curl`` command lines.

Authentication
^^^^^^^^^^^^^^

To use the API, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_ must be retrieved from ``https://FQDN/ucsschool-id-connector/api/token``. The token will be valid for a configurable amount of time (default 60 minutes), after which they must be renewed. To change the TTL, open the apps *app settings* in the UCS app center.

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/ucsschool-id-connector/api/token

Only members of the group ``ucsschool-id-connector-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes. In production only the regular admin user accounts should be used.


File locations
--------------

This section lists relevant directories and files. Configuration file *must not* be edited by hand. All configuration is done either trough the *app settings* in the UCS app center or through the *UCS\@school ID Connector HTTP API*.

Nothing needs to be backuped and restored before and after an app update, because all important data is persisted in files on volumes mounted from the UCS host into the docker container.

Logfiles
^^^^^^^^

``/var/log/univention/ucsschool-id-connector`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory contains:

* ``http.log``: log of the HTTP-API (both ASGI server and API application)
* ``queues.log``: log of the queue management daemon
* Old versions of above logfiles with timestamps appended to the file name. Logfile rotation happens mondays and 15 copies are kept.

Log output can also be seen running::

    $ docker logs <container name>

School authority configuration files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration of the replication targets (*school authorities / Schulträger*) is stored in one JSON file per configured school authority under ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/school_authorities``. The JSON configuration files must not be created by hand. The HTTP-API should be used for that instead.

Each school authority configuration has a queue associated.

Queue files
^^^^^^^^^^^

The LDAP listener process on the UCS host creates a JSON file for each creation/modification/move/deletion of a user object.
Those JSON files are written to ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/listener``. That is the directory of the *in queue*.

The process handling the *in queue* copies files from there to a directory for each school authority that it can associate with the user account in the file.
Each *out queue* handles a directory below ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues``.

When a school authority configuration is deleted, its associated queue directory is moved to ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/data/out_queues_trash``.

Token signature key
^^^^^^^^^^^^^^^^^^^

The key with which the JWTs are signed is in the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret``.
The file is created by the apps join script (see *Install* above).

SSL certificates for Kelvin client plugin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin that connects to the Kelvin API on the school authority side looks for and stores SSL certificates as ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/ssl_certs/HOSTNAME``. In case the certificate cannot be downloaded automatically, it can be saved there manually.

Volumes
^^^^^^^
The following directories are mounted from the host into the container:

* ``/var/lib/univention-appcenter/listener``
* ``/var/log/univention/ucsschool-id-connector``

Example setting up a second school authority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If we already have a school authority set up and want to basically copy its configuration in order to set up a second one we can do the following:

First make sure the new school authority server has the Kelvin app installed and running. Configuration is described in a later section.

Then we want to retrieve the configuration for our old school authority.
For this we open the HTTP-API Swagger UI ( https://FQDN/ucsschool-id-connector/api/v1/doc ) and authenticate ourselves.
The button can be found at the top right corner of the page.
Then we retrieve a list of the school authorities available using the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab, by clicking on ``Try it out`` and ``Execute``.
In the response body we get a JSON list of the school authorities that are currently configured.
We need to copy the one we want to replicate and save it for later.
Under "POST /ucsschool-id-connector/api/v1/school_authorities" we can create the new school authority.
Click *try it out* and insert the coped JSON object from before into the request body.
Now we just have to alter the name, url, and login credentials before executing the request.
The url has to point to the new school authorities HTTP-API.
The name can be chosen at your leisure and the password is the authentication token of the school authorities HTTP-API (retrieved earlier).
The tab ``PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`` can be used to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server one can use::

    $ udm settings/extended_attribute list


Installation of target HTTP-API (Kelvin)
----------------------------------------

On each target system run::

    $ univention-app install ucsschool-kelvin-rest-api

To allow the *UCS\@school ID Connector* app to access the APIs it needs an authorized user account. By default the Administrator account is the only authorized user. To add a dedicated Kelvin API user for the UCS@school ID-Connector consult the Kelvin documentation on how to do that.


Configuration of target HTTP-API (Kelvin)
-----------------------------------------
The Kelvin API must be version ``1.2.0`` or higher to work with the UCS@school ID Connector.
The password hashes for LDAP and Kerberos authentication are collectively transmitted in one JSON object to one target attribute.

The ``mapped_udm_properties`` setting lists the names of UDM properties that should be available in the API.
The example configuration above can be created with the following command::

   $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json \
      /var/lib/ucs-school-import/configs/kelvin.json
   $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/kelvin.json", "r+w"); \
      config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; \
      config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]; fp.seek(0); \
      json.dump(config, fp, indent=4, sort_keys=True); fp.close()'


ID Broker Plugin
----------------

The ID Broker plugin can be used to sync all users of all schools to one target, which we call ID Broker.
While doing so, other plugins like the kelvin plugin can still be used to sync specific
schools to school authorities defined in the school-to-authority mapping.

Installation and configuration of target HTTP-APIs (Kelvin & UCS@school APIs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On each target system run::

    $ univention-app install ucsschool-kelvin-rest-api
    $ univention-app install ucsschool-apis

and copy the the plugin code into the ucsschool-apis docker container.
The debian package ``id-broker-plugin`` takes care of this.

The steps to activate the provisioning-API are described in the id-broker-plugin readme of the repository.


Add this mapped_udm_property::

    $ echo '{ "mapped_udm_properties": ["brokerID"] }' > /var/lib/ucs-school-import/configs/kelvin.json
    $ univention-app shell ucsschool-kelvin-rest-api /etc/init.d/ucsschool-kelvin-rest-api restart

Create users which can use the internal kelvin-rest-api-client::

    $ udm users/user create --position "cn=users,$(ucr get ldap/base)" --set username=id-broker-kelvin-user --set firstname="ID Broker" --set lastname="Kelvin User" --set password=secret --append "groups=cn=ucsschool-kelvin-rest-api-admins,cn=groups,$(ucr get ldap/base)"


For each school authority, there must exist a provisioning user. For the school authority ``TEST`` do the following::

    $ udm users/user create --position "cn=users,$(ucr get ldap/base)" --set username=provisioning-TEST --set firstname="Provisioning User1" --set lastname="TEST" --set password=secet

Create a settings file for the ID Broker and replace IDBroker_IP with your IP::

    $ IDBroker_IP="1.2.3.4" # your IP
    $ echo "{ \"host\": \"$IDBroker_IP\", \"username\": \"id-broker-kelvin-user\", \"password\": \"secret\", \"verify_ssl\": false }" > /etc/ucsschool/apis/id_broker/settings.json
    $ univention-app restart ucsschool-apis




Configuration of school authorities
------------------------------------

POST the following JSON to ``https://SCHOOL_AUTH_FQDN/ucsschool-id-connector/api/v1/school_authorities``::

    {
        "name": "SchoolAuthorityName",
        "active": true,
        "url": "https://ID_BROKER_FQDN/",
        "plugins": ["id_broker-users", "id_broker-groups"],
        "plugin_configs": {
            "id_broker": {
                "password": "g3h31m",
                "username": "provisioning-SchoolAuthorityName",
                "version": 1
            }
        }
    }


We do not have to modify the mapping, because we only sync objects for schools of school authorities which have an ID Broker configuration.


Plugins
-------

The code of the *UCS\@school ID Connector* app can be adapted through plugins.
The `pluggy`_ plugin system is used to define, implement and call plugins.
To share code between plugins additional Python packages can be installed.
The following demonstrates a simple example of a custom Python packages and a plugin for *UCS\@school ID Connector*.

All plugin *specifications* (function signatures) are defined in ``src/ucsschool_id_connector/plugins.py``.

The directory structure for custom plugins and packages can be found in the host system below ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/``::

    /var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/plugins/
    /var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/plugins/packages/
    /var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/plugins/plugins/

The app is released with default plugins, that implement a default version for all specifications found in ``src/ucsschool_id_connector/plugins.py``.

An example plugin specification::

    class DummyPluginSpec:
        @hook_spec(firstresult=True)
        def dummy_func(self, arg1, arg2):
            """An example hook."""


A directory structure for a custom plugin ``dummy`` and custom package ``example_package`` below ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/``::

    .../plugins/
    .../plugins/packages
    .../plugins/packages/example_package
    .../plugins/packages/example_package/__init__.py
    .../plugins/packages/example_package/example_module.py
    .../plugins/plugins
    .../plugins/plugins/dummy.py


Content of ``plugins/plugins/dummy.py``::

    #
    # An example plugin that will be usable as "plugin_manager.hook.dummy_func()".
    # It uses a class from a module in a custom package:
    # plugins/packages/example_package/example_module.py
    #
    # The plugin specifications are in src/ucsschool_id_connector/plugins.py
    #

    from ucsschool_id_connector.utils import ConsoleAndFileLogging
    from ucsschool_id_connector.plugins import hook_impl, plugin_manager
    from example_package.example_module import ExampleClass

    logger = ConsoleAndFileLogging.get_logger(__name__)


    class DummyPlugin:
        @hook_impl
        def dummy_func(self, arg1, arg2):  # <-- this must match the specification!
            """
            Example plugin function.

            Returns the sum of its arguments.
            Uses a class from a custom package.
            """
            logger.info("Running DummyPlugin.dummy_func() with arg1=%r arg2=%r.", arg1, arg2)
            example_obj = ExampleClass()
            res = example_obj.add(arg1, arg2)
            assert res == arg1 + arg2
            return res


    # register plugins
    plugin_manager.register(DummyPlugin())

Content of ``plugins/packages/example_package/example_module.py``::

    #
    # An example Python module that will be loadable as "example_package.example_module"
    # if stored in 'plugins/packages/example_package/example_module.py'.
    # Do not forget to create 'plugins/packages/example_package/__init__.py'.
    #

    from ucsschool_id_connector.utils import ConsoleAndFileLogging

    logger = ConsoleAndFileLogging.get_logger(__name__)


    class ExampleClass:
        def add(self, arg1, arg2):
            logger.info("Running ExampleClass.add() with arg1=%r arg2=%r.", arg1, arg2)
            return arg1 + arg2

When the app starts, all plugins will be discovered and logged::

    ... INFO  [ucsschool_id_connector.plugins.load_plugins:83] Loaded plugins: {.., <dummy.DummyPlugin object at 0x7fa5284a9240>}
    ... INFO  [ucsschool_id_connector.plugins.load_plugins:84] Installed hooks: [.., 'dummy_func']


Kelvin Plugin Konfiguration
---------------------------

Until a full documentation is developed, only some specifics of the default Kelvin plugin are mentioned here

Role specific attribute mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With version ``2.1.0`` role specific attribute mapping was added to the default kelvin plugin. This allows to define
additional user mappings for each role (student, teacher, staff, school_admin) by adding a new mapping next to the
``users`` mapping suffixed by ``_$ROLE``, e.g. ``users_student: {}``.

If a user object is handled by the kelvin plugin the mapping is determined as follows:

- Determine all roles the user has in the schools the current school authority is configured to handle
- From that order the roles for priority with the school_admin being the highest followed by staff, teacher and
  then student.
- Choose a ``users_$ROLE`` mapping in that order from the ones configured in the plugin settings.
- If none was found, fall back to the ``users`` mapping as the default.

The mappings for the different roles are not additive because an additive approach would complicate the option
to remove mappings from a specific role. Only one mapping is chosen by the rules just described.

The priority order for the roles was chosen in order of common specificity in UCS@school. A student is usually ever only
a student. But teachers, staff and school admins can have multiple roles of those three.

Please be aware that removing the ``school_classes`` field in particular is not sufficient to prevent certain user roles
from being added or removed from school classes. This is due to the technical situation that changing the school classes
of a user does not only result in a user change event but also a school class change event, which is handled separately
and would add or remove the user in that way. To avoid this problem a derivate of the kelvin plugin can be used, which
is described in the following chapter.

Partial group sync
^^^^^^^^^^^^^^^^^^

With version ``2.1.0`` a new derivate of the ``kelvin`` plugin was added: ``kelvin-partial-group-sync``.
This plugin alters the handling of school class changes by allowing you to specify a list of roles that should be
ignored when syncing groups. The following steps determine which members are sent to a school authority when a
school class is added:

- Add all users that are members of the school class locally (Normal Kelvin plugin behavior).
- From that remove all users that have a configured role to ignore in any school handled by the school authority configuration.
- Get all members of the school class on the target system that have one of the configured roles and add them.
- Get all members of the school class on the target system that are unknown to the ID-Connector and add them.

This results in school classes having only members with roles not configured to ignore, plus members with roles to ignore
that were added on the target system, plus any users added on the target system which are unknown to the ID Connector.

To achieve this behavior several additional LDAP queries on the ID Connector and one additional request to
the target system are necessary.

To activate this alternative behavior replace the ``kelvin`` plugin in a school authority configuration with
``kelvin-partial-group-sync``. The configuration options are exactly the same as for the ``kelvin`` plugin, except for
the addition of ``school_classes_ignore_roles``, which holds the list of user roles to ignore for school class changes.

Please be aware that this plugin can only alter the handling of dedicated school class change events. Due to the
technical situation, changing the members of a school class often results in two events. A school class change and a
user change. To actually prevent users of certain roles being added to school classes at all, it is necessary to remove
the mapping of the users ``school_class`` field in the configuration as well.


.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.8-blue.svg
    :alt: Python 3.8
    :target: https://www.python.org/downloads/release/python-382/
.. |diagram_overview| image:: /ucsschool-id-connector/api/v1/static/ucsschool-id-connector_overview.png
    :alt: Diagram with an overview of the master 2 master sync
.. |ucsschool_id_connector_password_hook.py| image:: /ucsschool-id-connector/api/v1/static/ucsschool_id_connector_password_hook.py
    :alt: The UCS\@school import hook.
.. _pluggy: https://pluggy.readthedocs.io/
