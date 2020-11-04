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

The app is currently only available in the test appcenter. Installation::

    $ univention-install univention-appcenter-dev && univention-app dev-use-test-appcenter
    $ univention-app install ucsschool-id-connector

The join script ``50ucsschool-id-connector.inst`` must run and create:

* the file ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/tokens.secret`` containing the key with which JWT tokens are signed.
* the group ``ucsschool-id-connector-admins`` (with DN ``cn=ucsschool-id-connector-admins,cn=groups,$ldap_base``) whos members are allowed to access the HTTP-API.

If they didn't get created, run::

    $ univention-run-join-scripts --run-scripts --force 50ucsschool-id-connector.inst


On the target systems
^^^^^^^^^^^^^^^^^^^^^

A HTTP-API is required for the *UCS\@school ID Connector* app to be able to create/modify/delete users on the target systems. Currently only the BB-API is supported. Instructions for installation and configuration can be found in a later section.


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
            "bb": {
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

See ``src/example_configs.json`` for an example.


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

The plugin that connects to the Kelvin API on th school authority side looks for and stores SSL certificates as ``/var/lib/univention-appcenter/apps/ucsschool-id-connector/conf/ssl_certs/HOSTNAME``. In case the certificate cannot be downloaded automatically, it can be saved there manually.

Volumes
^^^^^^^
The following directories are mounted from the host into the container:

* ``/var/lib/univention-appcenter/listener``
* ``/var/log/univention/ucsschool-id-connector``

Example setting up a second school authority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If we already have a school authority set up and want to basically copy its configuration in order to set up a second one we can do the following:

First make sure the new school authority server has the package ucs-school-http-api-bb from the customer repository installed and running. Configuration is described in a later section.

Then we want to retrieve the configuration for our old school authority.
For this we open the HTTP-API Swagger UI ( https://FQDN/ucsschool-id-connector/api/v1/doc ) and authenticate ourselves.
The button can be found at the top right corner of the page.
Then we retrieve a list of the school authorities available using the ``GET /ucsschool-id-connector/api/v1/school_authorities`` tab, by clicking on ``Try it out`` and ``Execute``.
In the response body we get a JSON list of the school authorities that are currently configured.
We need to copy the one we want to replicate and save it for later.
Under "POST /ucsschool-id-connector/api/v1/school_authorities" we can create the new school authority.
Click *try it out* and insert the coped JSON object from before into the request body.
Now we just have to alter the name, url, and password before executing the request.
The url has to point to the new school authorities HTTP-API.
The name can be chosen at your leisure and the password is the authentication token of the school authorities HTTP-API (retrieved earlier).
The tab ``PATCH /ucsschool-id-connector/api/v1/school_authorities/{name}`` can be used to change an already existing configuration.

To retrieve a list of the extended attributes on the old school authority server one can use::

    $ udm settings/extended_attribute list


Installation of target HTTP-API
-------------------------------

On each target system run::

    $ echo -e "deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/all/\n\
      deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/amd64/" > \
      /etc/apt/sources.list.d/30_BB.list
    $ univention-install -y ucs-school-http-api-bb

To allow the *UCS\@school ID Connector* app to access the APIs it needs an authentication token. On each target system run::

    $ /usr/share/pyshared/bb/http_api/users/manage.py shell -c \
      "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)"

This will print the token for writing to the API to the screen. Copy and save it for later use.


Configuration of target HTTP-API
--------------------------------
The password hashes for LDAP and Kerberos authentication are collectively transmitted in one JSON object to one target attribute.
The target attributes name must be set in the school authority configuration attribute ``passwords_target_attribute``.
The target system is responsible for handling the data.

For UCS\@school target systems two extended attributes must be created.
The name of one (``ucsschool_id_connector_pw``) is used in the import hook `ucsschool_id_connector_password_hook.py <static/ucsschool_id_connector_password_hook.py>`_.
If the extended attributes name is not ``ucsschool_id_connector_pw``, the hook file ``ucsschool_id_connector_password_hook.py`` must be edited, as well as the school authority configuration and the BB-API configuration file (``/var/lib/ucs-school-import/configs/user_import.json``).
To install the extended attributes run::

    $ udm settings/extended_attribute create \
        --ignore_exists \
        --position "cn=custom attributes,cn=univention,$(ucr get ldap/base)" \
        --set name="ucsschool_id_connector_last_update" \
        --set CLIName="ucsschool_id_connector_last_update" \
        --set shortDescription="Date of last update by the UCS@school ID Connector app." \
        --set module="users/user" \
        --append options="ucsschoolStudent" \
        --append options="ucsschoolTeacher" \
        --append options="ucsschoolStaff" \
        --append options="ucsschoolAdministrator" \
        --set tabName="UCS@school" \
        --set tabPosition=9 \
        --set groupName="UCS@school ID Connector" \
        --set groupPosition="2" \
        --set translationGroupName='"de_DE" "UCS@school ID Connector"' \
       --set syntax=string \
        --set default="" \
        --set multivalue=0 \
        --set valueRequired=0 \
        --set mayChange=1 \
        --set doNotSearch=1 \
        --set objectClass=univentionFreeAttributes \
        --set ldapMapping=univentionFreeAttribute14 \
        --set deleteObjectClass=0 \
        --set overwriteTab=0 \
        --set fullWidth=1 \
        --set disableUDMWeb=0

    $ udm settings/extended_attribute create \
        --ignore_exists \
        --position "cn=custom attributes,cn=univention,$(ucr get ldap/base)" \
        --set name="ucsschool_id_connector_pw" \
        --set CLIName="ucsschool_id_connector_pw" \
        --set shortDescription="UCS@school ID Connector password sync." \
        --set module="users/user" \
        --append options="ucsschoolStudent" \
        --append options="ucsschoolTeacher" \
        --append options="ucsschoolStaff" \
        --append options="ucsschoolAdministrator" \
        --set syntax=string \
        --set default="" \
        --set multivalue=0 \
        --set valueRequired=0 \
        --set mayChange=1 \
        --set doNotSearch=1 \
        --set objectClass=univentionFreeAttributes \
        --set ldapMapping=univentionFreeAttribute15 \
        --set deleteObjectClass=0 \
        --set overwriteTab=0 \
        --set fullWidth=1 \
        --set disableUDMWeb=0

    $ wget https://SENDER-FQDN/ucsschool-id-connector/api/v1/static/ucsschool_id_connector_password_hook.py \
        -O /usr/share/ucs-school-import/pyhooks/ucsschool_id_connector_password_hook.py


Edit ``/var/lib/ucs-school-import/configs/user_import.json`` and add the name of the ``passwords_target_attribute`` (``ucsschool_id_connector_pw``) to ``mapped_udm_properties`` (and ``mapped_udm_properties`` to ``configuration_checks``)::

    "configuration_checks": ["defaults", "mapped_udm_properties"],
    "mapped_udm_properties": ["phone", "e-mail", "ucsschool_id_connector_pw"]

The ``mapped_udm_properties`` setting lists the names of UDM properties that should be available in the API.
The example configuration above can be created with the following command::

   $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json \
      /var/lib/ucs-school-import/configs/user_import.json
   $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/user_import.json", "r+w"); \
      config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; \
      config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]; fp.seek(0); \
      json.dump(config, fp, indent=4, sort_keys=True); fp.close()'


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
