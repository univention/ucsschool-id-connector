ID Sync replication system
==========================

|python| |license| |code style|

.. This file can be read on the installed system at https://FQDN/id-sync/api/v1/readme
.. The changelog can be read on the installed system at https://FQDN/id-sync/api/v1/history

Introduction
------------

The `ID Sync` replication system is composed of three components:

* A process on the data source UCS server, receiving user creation/modification/deletion events from the LDAP server and relaying them to multiple recipients via HTTP. Henceforth called the `ID Sync service`.
* A process on the data source UCS server to monitor and configure the ID Sync service, henceforth called the `ID Sync REST API`.
* Multiple recipients of the directory data relayed by the `ID Sync service`. They run a HTTP-API service, that the `ID Sync service` pushes updates to.

The changelog ist in the `HISTORY <history>`_ file.

Architectural overview
^^^^^^^^^^^^^^^^^^^^^^

|diagram_overview|


Interactions and components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

|diagram_details|


Development
-----------

Setup development environment::

    $ cd ~/git/id-sync
    $ make setup_devel_env
    $ make install

This will create a directory ``venv`` with a Python virtualenv with the app and all its dependencies in it. To use it, run::

    $ . venv/bin/activate

Run ``make`` without argument to see more useful commands::

    $ make

    clean                remove all build, test, coverage and Python artifacts
    clean-build          remove build artifacts
    clean-pyc            remove Python file artifacts
    clean-test           remove test and coverage artifacts
    setup_devel_env      setup development environment (virtualenv)
    lint                 check style (requires Python interpreter activated from venv)
    format               format source code (requires Python interpreter activated from venv)
    test                 run tests with the Python interpreter from 'venv'
    coverage             check code coverage with the Python interpreter from 'venv'
    coverage-html        generate HTML coverage report
    install              install the package to the active Python's site-packages
    build-docker-img     build docker image locally quickly
    build-docker-img-on-knut copy source to docker.knut, build and push docker image


Build Docker image::

    $ cd ~/git/id-sync
    $ make build-docker-img

The Docker image can be started on its own (but won't receive JSON files in the in queue from the listener in the host) by running::

    $ docker run -p 127.0.0.1:8911:8911/tcp --name id_sync docker-test-upload.software-univention.de/id-sync:0.1.0

Use ``docker run -d ...`` to let it run in the background. Use ``docker logs id_sync`` to see the stdout; ``docker stop id_sync`` and ``docker rm id_sync`` to stop and remove the running container.

Replace version (in above command ``0.1.0``) with current version. See ``APP_VERSION`` in output at the start of the build process.


When the container is started that way (not through the appcenter) it must be accessed through https://FQDN:8911/id-sync/api/v1/docs after stopping the firewall (``service univention-firewall stop``).

To enter the running container run::

    $ docker exec -it id_sync /bin/ash

There you can use the virtual envs Python::

    /id-sync # . venv/bin/activate

    (venv) /id-sync # python
    Python 3.7.4 (default, Aug  2 2019, 18:24:02)
    [GCC 8.3.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from id_sync import models

    (venv) /id-sync # ipython
    Python 3.7.4 (default, Aug  2 2019, 18:24:02)
    Type 'copyright', 'credits' or 'license' for more information
    IPython 7.8.0 -- An enhanced Interactive Python. Type '?' for help.

    In [1]: from id_sync import models


Install BB-API on sender for integration tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A HTTP-API is required for the integration tests (running in the container) to be able to create/modify/delete users in the host::

    $ ucr set bb/http_api/users/django_debug=yes bb/http_api/users/wsgi_server_capture_output=yes bb/http_api/users/wsgi_server_loglevel=debug bb/http_api/users/enable_session_authentication=yes
    $ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json /var/lib/ucs-school-import/configs/user_import.json
    $ python -c 'import json; fp = open("/var/lib/ucs-school-import/configs/user_import.json", "r+w"); config = json.load(fp); config["configuration_checks"] = ["defaults", "mapped_udm_properties"]; config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]; fp.seek(0); json.dump(config, fp, indent=4, sort_keys=True); fp.close()'
    $ echo -e "deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/all/\ndeb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-min-brandenburg/amd64/" > /etc/apt/sources.list.d/30_BB.list
    $ univention-install -y ucs-school-http-api-bb


Build release
-------------

To upload ("push") a new Docker image to Univentions Docker registry (``docker-test.software-univention.de``), run::

    $ cd ~/git/id-sync
    $ make build-docker-img-on-knut


Install
-------

The app is currently only available in the test appcenter. Installation::

    $ univention-install univention-appcenter-dev && univention-app dev-use-test-appcenter
    $ univention-app install id-sync

The join script ``50id-sync.inst`` must run and create:

* the file ``/var/lib/univention-appcenter/apps/id-sync/conf/tokens.secret`` containing the key with which JWT tokens are signed.
* the group ``id-sync-admins`` (with DN ``cn=id-sync-admins,cn=groups,$ldap_base``) whos members are allowed to access the HTTP-API.

If they didn't get created, run::

    $ univention-run-join-scripts --run-scripts --force 50id-sync.inst


Update
------

Updates are installed in one of the two usual UCS ways::

    $ univention-upgrade
    $ univention-app upgrade id-sync


Starting / Stopping services
----------------------------

Both services (`ID Sync service` and `ID Sync REST API`) run in a Docker container. The container can be started/stopped by using the regular service facility of the host system::

    $ service docker-app-id-sync start
    $ service docker-app-id-sync status
    $ service docker-app-id-sync stop

To restart individual services, init scripts `inside` the Docker container can be used::

    $ univention-app shell id-sync
    $ /etc/init.d/id-sync start  # status / stop (ID Sync service)
    $ /etc/init.d/id-sync-rest-api start # status / stop (ID Sync REST API)


Configuration
-------------
The school authorities configuration should be done through the `ID Sync REST API`.

The ``record_uid`` property should be synced to a UCS\@school system as ``record_uid``, the ``TODO`` property should be synced as ``roles``::

    {
        "mapping": {
            "record_uid": "record_uid",
            "TODO": "roles"
            }
    }

See ``src/example_configs.json`` for an example.

TODO: document what/how to map to "roles"


HTTP-API
--------

A HTTP-API offers two resources:

* `queues`: monitoring of queues
* `school_authorities`: configuration of school authorities

Two websites exist, that allow to interactively discover the API. They can be visited with a browser at the URLS:

* `Swagger UI <https://github.com/swagger-api/swagger-ui>`_: https://FQDN/id-sync/api/v1/docs
* `ReDoc <https://github.com/Rebilly/ReDoc>`_: https://FQDN/id-sync/api/v1/redoc

A `OpenAPI v3 (formerly "Swagger") schema <https://swagger.io/docs/specification/about/>`_ can be downloaded from https://FQDN/id-sync/api/v1/openapi.json

The Swagger UI page is especially helpful as it allows to send queries directly from the browser and displays equivalent ``curl`` command lines.

Authentication
^^^^^^^^^^^^^^

To use the API, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_ must be retrieved from ``https://FQDN/id-sync/api/token``. The token will be valid for a configurable amount of time (default 60 minutes), after which they must be renewed. To change the TTL, open the apps `app settings` in the app center.

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/id-sync/api/token

Only members of the group ``id-sync-admins`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes. In production the regular admin user accounts should be used.


File locations
--------------

Nothing need to be backuped and restored before and after an app update, because all important data is persisted in files on volumes  mounted from the UCS host into the docker container.

Logfiles
^^^^^^^^

``/var/log/univention/id-sync`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory contains:

* ``http.log``: log of the HTTP-API (both ASGI server and API application)
* ``queues.log``: log of the queue management daemon
* Old versions of above logfiles with timestamps appended to the file name. Logfile rotation happens mondays and 15 copies are kept.

Log output can also be seen running::

    $ docker logs <container name>

School authority configuration files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration of the replication targets (`school authorities / Schulträger`) is stored in one JSON file per configured school authority under ``/var/lib/univention-appcenter/apps/id-sync/conf/school_authorities``. The JSON configuration files must not be created by hand. The HTTP-API should be used for that instead.

Each school authority configuration has a queue associated.

Queue files
^^^^^^^^^^^

The listener on the UCS host creates a JSON file for each creation/modification/move/deletion of a user object.
Those JSON files are written to ``/var/lib/univention-appcenter/apps/id-sync/data/listener``. That is the directory of the `in queue`.

The process handling the `in queue` copies files from it to a directory for each school authority that it can associate with the user account in the file.
Each `out queue` handles a directory below ``/var/lib/univention-appcenter/apps/id-sync/data/out_queues``.

When a school authority configuration is deleted, its associated queue directory is moved to ``/var/lib/univention-appcenter/apps/id-sync/data/out_queues_trash``.

Token signature key
^^^^^^^^^^^^^^^^^^^

The key with which the JWTs are signed is in the file ``/var/lib/univention-appcenter/apps/id-sync/conf/tokens.secret``.
The file is created by the apps join script (see `Install` above).

Volumes
^^^^^^^
The following directories are mounted from the host into the container:

* ``/var/lib/univention-appcenter/listener``
* ``/var/log/univention/id-sync``

Example setting up a second school authority
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If we already have a school authority set up and want to basically copy its configuration in order to set up a second one we can do the following:

First make sure the new school authority server has the package ucs-school-http-api-bb from the custumer repository installed and running.

First we want to retrieve the configuration for our old school authority. For this we open the HTTP-API Swagger UI ( https://FQDN/id-sync/api/v1/doc ) and authenticate ourselves. The button can be found at the top right corner of the page. Then we retrieve a list of the school authorities available using the ``GET /id-sync/api/v1/school_authorities`` tab, by clicking on ``Try it out`` and ``Execute``. In the response body we get a JSON list of the school authorities that are currently configured. We need to copy the one we want to replicate and save it for later. Under "POST /id-sync/api/v1/school_authorities" we can create the new school authority. Click `try it out` and insert the coped JSON object from before into the request body. Now we just have to alter the name, url, and password before executing the request. The url has to point to the new school authorities HTTP-API. The name can be chosen at your leisure and the password is the authentication token of the school authorities HTTP-API. The tab ``PATCH /id-sync/api/v1/school_authorities/{name}`` can be used to change an already existing configuration.

How the HTTP-API of the target school authority can be set is described in the following section. To retrieve a list of the extended attributes on the old school authority server one can use::

    $ udm settings/extended_attribute list


Configuration of target HTTP-API
--------------------------------
The password hashes for LDAP and Kerberos authentication are collectively transmitted in one JSON object to one target attribute.
The target attributes name must be set in the school authority configuration attribute ``passwords_target_attribute``. The target system is responsible for handling the data.

For UCS\@school target systems an extended attribute must be created and its name used in the import hook provided in ``target_systems/usr/share/ucs-school-import/pyhooks/handle_id_sync_pw.py``::

    $ udm settings/extended_attribute create \
        --ignore_exists \
        --position "cn=custom attributes,cn=univention,$(ucr get ldap/base)" \
        --set name="id_sync_last_update" \
        --set CLIName="id_sync_last_update" \
        --set shortDescription="Date of last update by the ID Sync app." \
        --set module="users/user" \
        --append options="ucsschoolStudent" \
        --append options="ucsschoolTeacher" \
        --append options="ucsschoolStaff" \
        --append options="ucsschoolAdministrator" \
        --set tabName="UCS@school" \
        --set tabPosition=9 \
        --set groupName="ID Sync" \
        --set groupPosition="2" \
        --set translationGroupName='"de_DE" "ID Sync"' \
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
        --set name="id_sync_pw" \
        --set CLIName="id_sync_pw" \
        --set shortDescription="ID Sync password sync." \
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

    $ cp target_systems/usr/share/ucs-school-import/pyhooks/handle_id_sync_pw.py \
        /usr/share/ucs-school-import/pyhooks/


Edit ``/var/lib/ucs-school-import/configs/user_import.json`` and add the name of the `passwords_target_attribute` (``id_sync_pw``) to ``mapped_udm_properties``::

    "mapped_udm_properties": ["phone", "e-mail", "id_sync_pw"]


**Attention**: if the password target property is not named ``id_sync_pw``, the constant at the top of the import hook (``handle_id_sync_pw.py``) must be modified accordingly (as well as the school authority configuration and the BB-HTTP-API configuration).


Tests
-----

Unit tests are executed as part of the build process. To start them manually in the installed apps running Docker container, run::

    root@ucs-host:# univention-app shell id-sync
    /id-sync # cd src/
    /id-sync/src # /id-sync/venv/bin/python -m pytest -l -v unittests
    /id-sync/src # exit

To run integration tests (*not safe, will modify source and target systems!*), run::

    root@ucs-host:# univention-app shell id-sync
    /id-sync # cd src/
    /id-sync/src # /id-sync/venv/bin/python -m pytest -l -v integration_tests
    /id-sync/src # exit


TODOs
-----

* Fix BB-API:

  * search with unknown property returns all objects (``/api-bb/users/?ucsschoolSourceUID=TESTID&foobar=abc -> all user objects``)


.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.7+-blue.svg
    :alt: Python 3.7+
    :target: https://www.python.org/downloads/release/python-373/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/python/black
.. |diagram_overview| image:: /id-sync/api/v1/static/M2M-Sync_overview.png
    :alt: Diagram with an overview of the master 2 master sync
.. |diagram_details| image:: /id-sync/api/v1/static/M2M-Sync_details.png
    :alt: Diagram with the technical details of the master 2 master sync
